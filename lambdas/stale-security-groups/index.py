#!/usr/bin/env python3

# Original script from https://gist.github.com/astrikos/d782c2108d4bebaabbbd1528d2c3821d/a1ae81a3c0c39ccff7b64e52603243985130b4d0
# Corey Quinn (twitter.com/Quinnypig) called it "It's just a hop, skip, and a jump from being turned into a Lambda function..."
# I, Joe Gardner (github.com/joehack3r/aws), considered this a challenge and thus made it a lambda.
# In reality, script needs to address AWS API calls returning multiple pages of results. Maybe somebody else will take that challenge.

import boto3
import argparse
import os


class StaleSGDetector(object):
    """
    Class to hold the logic for detecting AWS security groups that are stale.
    """

    def __init__(self, **kwargs):
        super(StaleSGDetector, self).__init__()
        # self.region = kwargs["region"]
        # self.profile = kwargs["profile"]
        self.all_groups = set()
        self.security_groups_in_use = set()
        self.stale_groups = set()
        self.ec2_instances_count = 0
        self.network_interfaces_count = 0
        self.elbs_count = 0
        self.albs_count = 0
        self.rds_count = 0
        self.redshift_count = 0

    def get_session(self):
        """Gets a new boto3 session"""
        kwargs = {}
        # kwargs['profile_name'] = self.profile
        # kwargs['region_name'] = self.region
        session = boto3.Session(**kwargs)
        return session

    def run(self):
        self.session = self.get_session()
        self.get_all_security_groups()
        self.get_ec2_security_groups()
        self.get_launchconfig_security_groups()
        self.get_network_interfaces_security_groups()
        self.get_elb_security_groups()
        self.get_alb_security_groups()
        self.get_rds_security_groups()
        self.get_redshift_security_groups()
        self.calculate_stale_security_groups()

    def get_all_security_groups(self):
        """Adds all existing security groups used in the region."""
        ec2_client = self.session.client('ec2')
        security_groups_dict = ec2_client.describe_security_groups()
        security_groups = security_groups_dict['SecurityGroups']
        for group in security_groups:
            # Default SGs don't have to be deleted.
            if group['GroupName'] == 'default':
                self.security_groups_in_use.add(group['GroupId'])
            # SGs managed by CloudFormation don't have to be deleted.
            if 'Tags' in group:
                for tag in group['Tags']:
                    if tag['Key'] == 'aws:cloudformation:stack-id':
                        self.security_groups_in_use.add(group['GroupId'])
            self.all_groups.add(group['GroupId'])

    def get_ec2_security_groups(self):
        """Adds security groups used by EC2 instances."""
        ec2_client = self.session.client('ec2')
        instances = ec2_client.describe_instances()
        reservations = instances['Reservations']

        for reservation in reservations:
            for instance in reservation['Instances']:
                self.ec2_instances_count += 1
                for group in instance['SecurityGroups']:
                    self.security_groups_in_use.add(group['GroupId'])

    def get_launchconfig_security_groups(self):
        """Adds security groups used by Launch Configurations instances."""
        asg_client = self.session.client('autoscaling')
        launch_configurations = asg_client.describe_launch_configurations()
        for launch_config in launch_configurations['LaunchConfigurations']:
            for group in launch_config['SecurityGroups']:
                self.security_groups_in_use.add(group)

    def get_network_interfaces_security_groups(self):
        """Adds security groups used by Network Interfaces (ENIs)."""
        ec2_client = self.session.client('ec2')
        enis = ec2_client.describe_network_interfaces()
        for eni in enis['NetworkInterfaces']:
            self.network_interfaces_count += 1
            for group in eni['Groups']:
                self.security_groups_in_use.add(group['GroupId'])

    def get_elb_security_groups(self):
        """Adds security groups used by classic elastic loadbalancers (ELBs)."""
        elb_client = self.session.client('elb')
        elbs = elb_client.describe_load_balancers()
        for elb in elbs['LoadBalancerDescriptions']:
            self.elbs_count += 1
            for group in elb['SecurityGroups']:
                self.security_groups_in_use.add(group)

    def get_alb_security_groups(self):
        """Adds security groups used by application loadbalancers (ALBs)."""
        alb_client = self.session.client('elbv2')
        albs = alb_client.describe_load_balancers()
        for alb in albs['LoadBalancers']:
            self.albs_count += 1
            for group in alb['SecurityGroups']:
                self.security_groups_in_use.add(group)

    def get_rds_security_groups(self):
        """Adds security groups used by RDS."""
        rds_client = self.session.client('rds')
        rdses = rds_client.describe_db_instances()
        for rds in rdses['DBInstances']:
            self.rds_count += 1
            for group in rds['VpcSecurityGroups']:
                self.security_groups_in_use.add(group['VpcSecurityGroupId'])

    def get_redshift_security_groups(self):
        """Adds security groups used by Redshift."""
        redshift_client = self.session.client('redshift')
        redshifts = redshift_client.describe_clusters()
        for cluster in redshifts['Clusters']:
            self.redshift_count += 1
            for group in cluster['VpcSecurityGroups']:
                self.security_groups_in_use.add(group['VpcSecurityGroupId'])

    def calculate_stale_security_groups(self):
        self.stale_groups = self.all_groups.difference(self.security_groups_in_use)

        # Check if there is a SG in usd SGs but not in all.
        # Could that ever be true?
        assert (not self.security_groups_in_use.difference(self.all_groups))


def report(detector_object):
    print("---------------")

    search_log = (
        "Searched through {} EC2 instances, "
        "{} network interfaces, {} ELBs, {} ALBs, "
        "{} RDS instances, {} Redshift clusters"
    ).format(
        detector_object.ec2_instances_count,
        detector_object.network_interfaces_count,
        detector_object.elbs_count, detector_object.albs_count,
        detector_object.rds_count, detector_object.redshift_count
    )
    print(search_log)

    sg_log = "Found {} Security Groups in total, which {} are in-use.".format(
        len(detector_object.all_groups), len(detector_object.security_groups_in_use)
    )
    print(sg_log)

    stale_log = "Following {} security groups don't seem to be used:".format(
        len(detector_object.stale_groups)
    )
    print(stale_log)

    for sg in detector_object.stale_groups:
        print("  - ", sg)

    print("---------------")


def send_sns(detector_object):
    if len(detector_object.stale_groups) > 0:
        message = "The following Security Groups were identified as stale: {}".format(detector_object.stale_groups)

        boto3.client('sns').publish(
            TargetArn=os.environ['sns_topic_arn'],
            Message=message,
            Subject="Lambda Monitor: Stale Security Groups"
        )


def lambda_handler(event, context):
    detector = StaleSGDetector()
    detector.run()
    send_sns(detector)


if __name__ == "__main__":
    # Uncomment following two lines if want to test/debug/run/emulate lambda
    # lambda_handler("foo", "bar")
    # sys.exit(0)

    parser = argparse.ArgumentParser(description="Show unused security groups")
    parser.add_argument(
        "-p", "--profile", type=str, default="default",
        help="The AWS profile that will be used."
    )
    parser.add_argument(
        "-r", "--region", type=str, default="eu-west-1",
        help="The default region is eu-west-1."
    )
    parser.add_argument(
        "-d", "--delete", help="Delete security groups from AWS",
        action="store_true"
    )
    parser.add_argument(
        "-n", "--no-report", help="Skip showing report for Security Groups",
        action="store_true", default=False
    )
    args = parser.parse_args()

    detector = StaleSGDetector(
        **{"region": args.region, "profile": args.profile}
    )
    detector.run()

    if not args.no_report:
        report(detector)
