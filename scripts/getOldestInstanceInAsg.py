#!/usr/bin/env python
import boto.ec2.autoscale
import logging
import sys
import urllib2

logging.basicConfig(level=logging.ERROR,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M'
                    )

def getLaunchNumber(resourceId):
  # From reading http://www.jackofallclouds.com/2009/09/anatomy-of-an-amazon-ec2-resource-id/
  # and http://www.rightscale.com/blog/cloud-industry-insights/amazon-usage-estimates
  numeric_id = int(resourceId.split('-')[1], 16)

  p1 = numeric_id >> 24
  p2 = (numeric_id >> 16) & 0xFF
  p3 = numeric_id & 0xFFFF
  p3_1 = (numeric_id >> 8) & 0xFF
  p3_2 = numeric_id & 0xFF

  c1 = p1 ^ p3_2 ^ 0x69
  c2 = p2 ^ p3_1 ^ 0xe5
  c3 = p3 ^ 0x4000

  c1 = str(c1).zfill(3)
  c2 = str(c2).zfill(3)
  c3 = str(c3).zfill(5)

  launchNumber = int(c1 + c2 + c3)
  return format(launchNumber, 'x')

# User defined variables

# Other variables
instanceId=urllib2.urlopen("http://169.254.169.254/latest/meta-data/instance-id").read()
az=urllib2.urlopen("http://169.254.169.254/latest/meta-data/placement/availability-zone").read()
region=az[:-1]

#Can use IAM role, environment variables (see https://github.com/boto/boto), or specify credentials here.
# accessKey = "" # change to your access key
# secretKey = "" # change to your secret access key
try:
  accessKey
  secretKey
  ec2 = boto.ec2.connect_to_region(region,aws_access_key_id=accessKey,aws_secret_access_key=secretKey)
  asg = boto.ec2.autoscale.connect_to_region(region,aws_access_key_id=accessKey,aws_secret_access_key=secretKey)
except NameError:
  ec2 = boto.ec2.connect_to_region(region)
  asg = boto.ec2.autoscale.connect_to_region(region)

#Determine which autoscaling group this instance is a member of
if ec2.get_only_instances(instance_ids=instanceId)[0].tags.get('aws:autoscaling:groupName') is None:
  print "Instance is not part of an autoscaling group... exiting."
  sys.exit(0)
else:
  asgName=ec2.get_only_instances(instance_ids=instanceId)[0].tags.get('aws:autoscaling:groupName')
  logging.info("Instance %s is a member of the following autoscaling group: %s" % (instanceId, asgName))

asgGroup = asg.get_all_groups(names=[asgName])[0]
asgInstanceIds = [i.instance_id for i in asgGroup.instances]
oldestInstance = instanceId
for instance in asgInstanceIds:
  logging.info("InstanceId: " + instance + "; InstanceLaunchNumber: " + getLaunchNumber(instance))
  if getLaunchNumber(instance) < getLaunchNumber(oldestInstance):
    oldestInstance = instance

print oldestInstance
sys.exit(0)
