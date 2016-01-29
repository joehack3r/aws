#!/usr/bin/env bash

# Need statsd-client installed
# curl -o https://raw.githubusercontent.com/etsy/statsd/master/examples/statsd-client.sh /usr/local/bin/statsd-client
command -v statsd-client >/dev/null 2>&1 || { echo >&2 "statsd-client not installed. Please run: curl -o /usr/local/bin/statsd-client https://raw.githubusercontent.com/etsy/statsd/master/examples/statsd-client.sh; chmod 755 /usr/local/bin/statsd-client"; exit 1; }


#Variables
decimal=2
errorLimit=90
warningLimit=80

# Environment variables
az=`curl --max-time 1 -l http://169.254.169.254/latest/meta-data/placement/availability-zone 2>/dev/null`
if [ -z "$az" ]; then
  echo "What region do you want to check?"
  read region
else
  region=${az%?}
fi

## AWS Limits
EbsSnapshotCountLimit=10000
EbsVolumeCountLimit=5000

# Default is 20000 GiB (20 TiB).
EbsStandardStorageSizeLimit=20000
EbsGp2StorageSizeLimit=20000
EbsIo1StorageSizeLimit=20000

# Default is 40000 Provisioned IOPS
EbsProvisionedIopsLimit=40000

# Default is 20 On-Demand or Reserved Instances.
Ec2OnDemandInstanceCountLimit=20

# Default is 100 Spot Instances.
Ec2SpotInstanceCountLimit=100

# Default is 5 Elastic IPs.
Ec2ElasticIpCountLimit=5

# Default is 25 Elastic Load Balancer.
Ec2ElasticLoadBalancerCountLimit=25

# Default is 20 CloudFormation Stacks.
CfnStackCountLimit=20

# Default is 20 Auto Scaling Groups.
AutoScalingGroupCountLimit=20

# Default is 100 Launch Configurations.
LaunchConfigurationCountLimit=100

# Default is 50 Manual Snapshots.
RdsManualSnapshotsCountLimit=50

# Default is 5 VPCs.
VpcCountLimit=5


# Get current usage
EbsSnapshotCountUsed=`aws ec2 describe-snapshots --owner-ids self --region $region --output json | grep SnapshotId | wc -l`
EbsVolumeCountUsed=`aws ec2 describe-volumes --region $region --output json | grep VolumeId | tr --delete [:blank:] | uniq | wc -l`
EbsStandardStorageSizeUsed=`aws ec2 describe-volumes --filters Name=volume-type,Values=standard --region $region --output json | grep Size | awk '{print $2}' | awk '{sum=0} {sum+=$1} END {if (sum=="") print 0; else print sum}'`
EbsGp2StorageSizeUsed=`aws ec2 describe-volumes --filters Name=volume-type,Values=gp2 --region $region --output json | grep Size | awk '{print $2}' | awk '{sum=0} {sum+=$1} END {if (sum=="") print 0; else print sum}'`
EbsIo1StorageSizeUsed=`aws ec2 describe-volumes --filters Name=volume-type,Values=io1 --region $region --output json | grep Size | awk '{print $2}' | awk '{sum=0} {sum+=$1} END {if (sum=="") print 0; else print sum}'`
EbsProvisionedIopsUsed=`aws ec2 describe-volumes --filters Name=volume-type,Values=io1 --region $region --output json | grep Iops | awk '{print $2}' | awk '{sum=0} {sum+=$1} END {if (sum=="") print 0; else print sum}'`

Ec2InstanceCountUsed=`aws ec2 describe-instances --region $region --output json | grep InstanceId | wc -l`
Ec2SpotInstanceCountUsed=`aws ec2 describe-instances --filters Name=instance-lifecycle,Values=spot --region $region --output json | grep InstanceId | wc -l`
Ec2OnDemandInstanceCountUsed=`echo $Ec2InstanceCountUsed-$Ec2SpotInstanceCountUsed | bc`

Ec2ElasticIpCountUsed=`aws ec2 describe-addresses --region $region --output json | grep InstanceId | wc -l`
Ec2ElasticLoadBalancerCountUsed=`aws elb describe-load-balancers --region $region --output json | grep LoadBalancerName | wc -l`
CfnStackCountUsed=`aws cloudformation describe-stacks --region $region --output json | grep StackName | wc -l`

AutoScalingGroupCountUsed=`aws autoscaling describe-auto-scaling-groups --region $region --output json | grep AutoScalingGroupName | wc -l`
LaunchConfigurationCountUsed=`aws autoscaling describe-launch-configurations --region $region --output json | grep "LaunchConfigurationName" | wc -l`

RdsManualSnapshotsCountUsed=`aws rds describe-db-snapshots --snapshot-type manual --region $region --output json | grep "DBSnapshotIdentifier" | wc -l`

VpcCountUsed=`aws ec2 describe-vpcs --region $region --output json | grep VpcId | wc -l`


# Convert to percentages
EbsSnapshotCountPercentUsed=`echo "scale=$decimal; 100 * $EbsSnapshotCountUsed / $EbsSnapshotCountLimit" | bc`;
EbsVolumeCountPercentUsed=`echo "scale=$decimal; 100 * $EbsVolumeCountUsed / $EbsVolumeCountLimit" | bc`
EbsStandardStorageSizePercentUsed=`echo "scale=$decimal; 100 * $EbsStandardStorageSizeUsed / $EbsStandardStorageSizeLimit" | bc`
EbsGp2StorageSizePercentUsed=`echo "scale=$decimal; 100 * $EbsGp2StorageSizeUsed / $EbsGp2StorageSizeLimit" | bc`
EbsIo1StorageSizePercentUsed=`echo "scale=$decimal; 100 * $EbsIo1StorageSizeUsed / $EbsIo1StorageSizeLimit" | bc`
EbsProvisionedIopsPercentUsed=`echo "scale=$decimal; 100 * $EbsProvisionedIopsUsed / $EbsProvisionedIopsLimit" | bc`
Ec2OnDemandInstanceCountPercentUsed=`echo "scale=$decimal; 100 * $Ec2OnDemandInstanceCountUsed / $Ec2OnDemandInstanceCountLimit" | bc`
Ec2SpotInstanceCountPercentUsed=`echo "scale=$decimal; 100 * $Ec2SpotInstanceCountUsed / $Ec2SpotInstanceCountLimit" | bc`
Ec2ElasticIpCountPercentUsed=`echo "scale=$decimal; 100 * $Ec2ElasticIpCountUsed / $Ec2ElasticIpCountLimit" | bc`
Ec2ElasticLoadBalancerCountPercentUsed=`echo "scale=$decimal; 100 * $Ec2ElasticLoadBalancerCountUsed / $Ec2ElasticLoadBalancerCountLimit" | bc`
CfnStackCountPercentUsed=`echo "scale=$decimal; 100 * $CfnStackCountUsed / $CfnStackCountLimit" | bc`
AutoScalingGroupCountPercentUsed=`echo "scale=$decimal; 100 * $AutoScalingGroupCountUsed / $AutoScalingGroupCountLimit" | bc`
LaunchConfigurationCountPercentUsed=`echo "scale=$decimal; 100 * $LaunchConfigurationCountUsed / $LaunchConfigurationCountLimit" | bc`
RdsManualSnapshotsCountPercentUsed=`echo "scale=$decimal; 100 * $RdsManualSnapshotsCountUsed / $RdsManualSnapshotsCountLimit" | bc`
VpcCountPercentUsed=`echo "scale=$decimal; 100 * $VpcCountUsed / $VpcCountLimit" | bc`



#Echo usage and percentage to stdout, and statsd
echo "EBS Snapshot Count Used:"                                       $EbsSnapshotCountUsed
echo "EBS Volume Count Used:"                                         $EbsVolumeCountUsed
echo "EBS Standard (Magnetic) Storage Size Used:"                     $EbsStandardStorageSizeUsed
echo "EBS GP2 (General Purpose SSD) Storage Size Used:"               $EbsGp2StorageSizeUsed
echo "EBS IO1 (Provisioned IOPS) Storage Size Used:"                  $EbsIo1StorageSizeUsed
echo "EBS Provisioned IOPS Used:"                                     $EbsProvisionedIopsUsed
echo "EC2 OnDemand Instance Count Used:"                              $Ec2OnDemandInstanceCountUsed
echo "EC2 Spot Instance Count Used:"                                  $Ec2SpotInstanceCountUsed
echo "EC2 Elastic IP Count Used:"                                     $Ec2ElasticIpCountUsed
echo "EC2 Elastic Load Balancer Count Used:"                          $Ec2ElasticLoadBalancerCountUsed
echo "CloudFormation Stack Count Used:"                               $CfnStackCountUsed
echo "Auto Scaling Group Count Used:"                                 $AutoScalingGroupCountUsed
echo "Launch Configuration Count Used:"                               $LaunchConfigurationCountUsed
echo "RDS Manual Snapshot Count Used:"                                $RdsManualSnapshotsCountUsed
echo "VPC Count Used:"                                                $VpcCountUsed



echo "EBS Snapshot Count Percentage Used:"                            $EbsSnapshotCountPercentUsed
echo "EBS Volume Count Percentage Used:"                              $EbsVolumeCountPercentUsed
echo "EBS Standard (Magnetic) Storage Percentage Size Used:"          $EbsStandardStorageSizePercentUsed
echo "EBS GP2 (General Purpose SSD) Storage Percentage Size Used:"    $EbsGp2StorageSizePercentUsed
echo "EBS IO1 (Provisioned IOPS) Storage Percentage Size Used:"       $EbsIo1StorageSizePercentUsed
echo "EBS Provisioned IOPS Percentage Used:"                          $EbsProvisionedIopsPercentUsed
echo "EC2 OnDemand Instance Count Percentage Used:"                   $Ec2OnDemandInstanceCountPercentUsed
echo "EC2 Spot Instance Count Percentage Used:"                       $Ec2SpotInstanceCountPercentUsed
echo "EC2 Elastic IP Count Percentage Used:"                          $Ec2ElasticIpCountPercentUsed
echo "EC2 Elastic Load Balancer Count Percentage Used:"               $Ec2ElasticLoadBalancerCountPercentUsed
echo "CloudFormation Stack Count Percentage Used:"                    $CfnStackCountPercentUsed
echo "Auto Scaling Group Count Percentage Used:"                      $AutoScalingGroupCountPercentUsed
echo "Launch Configuration Count Percentage Used:"                    $LaunchConfigurationCountPercentUsed
echo "RDS Manual Snapshot Count Percentage Used:"                     $RdsManualSnapshotsCountPercentUsed
echo "VPC Count Percentage Used:"                                     $VpcCountPercentUsed


statsd-client "my.ebs.snapshotcount.used:$EbsSnapshotCountUsed|g"
statsd-client "my.ebs.volumecount.used:$EbsVolumeCountUsed|g"
statsd-client "my.ebs.standardstoragesize.used:$EbsStandardStorageSizeUsed|g"
statsd-client "my.ebs.gp2storagesize.used:$EbsGp2StorageSizeUsed|g"
statsd-client "my.ebs.io1storagesize.used:$EbsIo1StorageSizeUsed|g"
statsd-client "my.ebs.provisionediops.used:$EbsProvisionedIopsUsed|g"
statsd-client "my.ec2.ondemandinstancecount.used:$Ec2OnDemandInstanceCountUsed|g"
statsd-client "my.ec2.spotinstancecount.used:$Ec2SpotInstanceCountUsed|g"
statsd-client "my.ec2.elasticipcount.used:$Ec2ElasticIpCountUsed|g"
statsd-client "my.ec2.elasticloadbalancercount.used:$Ec2ElasticLoadBalancerCountUsed|g"
statsd-client "my.cfn.stackcount.used:$CfnStackCountUsed|g"
statsd-client "my.ec2.autoscalinggroupcount.used:$AutoScalingGroupCountUsed|g"
statsd-client "my.ec2.launchconfigurationcount.used:$LaunchConfigurationCountUsed|g"
statsd-client "my.rds.manualsnapshotcount.used:$RdsManualSnapshotsCountUsed|g"
statsd-client "my.vpc.count.used:$VpcCountUsed|g"

statsd-client "my.ebs.snapshotcount.used.percentage:$EbsSnapshotCountPercentUsed|g"
statsd-client "my.ebs.volumecount.used.percentage:$EbsVolumeCountPercentUsed|g"
statsd-client "my.ebs.standardstoragesize.used.percentage:$EbsStandardStorageSizePercentUsed|g"
statsd-client "my.ebs.gp2storagesize.used.percentage:$EbsGp2StorageSizePercentUsed|g"
statsd-client "my.ebs.io1storagesize.used.percentage:$EbsIo1StorageSizePercentUsed|g"
statsd-client "my.ebs.provisionediops.used.percentage:$EbsProvisionedIopsPercentUsed|g"
statsd-client "my.ec2.ondemandinstancecount.used.percentage:$Ec2OnDemandInstanceCountPercentUsed|g"
statsd-client "my.ec2.spotinstancecount.used.percentage:$Ec2SpotInstanceCountPercentUsed|g"
statsd-client "my.ec2.elasticipcount.used.percentage:$Ec2ElasticIpCountPercentUsed|g"
statsd-client "my.ec2.elasticloadbalancercount.used.percentage:$Ec2ElasticLoadBalancerCountPercentUsed|g"
statsd-client "my.cfn.stackcount.used.percentage:$CfnStackCountPercentUsed|g"
statsd-client "my.ec2.autoscalinggroup.used.percentage:$AutoScalingGroupCountPercentUsed|g"
statsd-client "my.ec2.launchconfiguration.used.percentage:$LaunchConfigurationCountPercentUsed|g"
statsd-client "my.rds.manualsnapshotcount.used.percentage:$RdsManualSnapshotsCountPercentUsed|g"
statsd-client "my.vpc.count.used:$VpcCountPercentUsed|g"


if
  [[ $(echo " $EbsSnapshotCountPercentUsed > $errorLimit" | bc) -eq 1 ]] ||
  [[ $(echo " $EbsVolumeCountPercentUsed > $errorLimit" | bc) -eq 1 ]] ||
  [[ $(echo " $EbsStandardStorageSizePercentUsed > $errorLimit" | bc) -eq 1 ]] ||
  [[ $(echo " $EbsGp2StorageSizePercentUsed > $errorLimit" | bc) -eq 1 ]] ||
  [[ $(echo " $EbsIo1StorageSizePercentUsed > $errorLimit" | bc) -eq 1 ]] ||
  [[ $(echo " $EbsProvisionedIopsPercentUsed > $errorLimit" | bc) -eq 1 ]] ||
  [[ $(echo " $Ec2OnDemandInstanceCountPercentUsed > $errorLimit" | bc) -eq 1 ]] ||
  [[ $(echo " $Ec2SpotInstanceCountPercentUsed > $errorLimit" | bc) -eq 1 ]] ||
  [[ $(echo " $Ec2ElasticIpCountPercentUsed > $errorLimit" | bc) -eq 1 ]] ||
  [[ $(echo " $Ec2ElasticLoadBalancerCountPercentUsed > $errorLimit" | bc) -eq 1 ]] ||
  [[ $(echo " $CfnStackCountPercentUsed > $errorLimit" | bc) -eq 1 ]] ||
  [[ $(echo " $AutoScalingGroupCountPercentUsed > $errorLimit" | bc) -eq 1 ]] ||
  [[ $(echo " $LaunchConfigurationCountPercentUsed > $errorLimit" | bc) -eq 1 ]] ||
  [[ $(echo " $RdsManualSnapshotsCountPercentUsed > $errorLimit" | bc) -eq 1 ]] ||
  [[ $(echo " $VpcCountPercentUsed > $errorLimit" | bc) -eq 1 ]]
  then
    echo "Using over $errorLimit% of a monitored AWS limit"
    statsd-client "my.aws.limits.error:2|g"
elif
  [[ $(echo " $EbsSnapshotCountPercentUsed > $warningLimit" | bc) -eq 1 ]] ||
  [[ $(echo " $EbsVolumeCountPercentUsed > $warningLimit" | bc) -eq 1 ]] ||
  [[ $(echo " $EbsStandardStorageSizePercentUsed > $warningLimit" | bc) -eq 1 ]] ||
  [[ $(echo " $EbsGp2StorageSizePercentUsed > $warningLimit" | bc) -eq 1 ]] ||
  [[ $(echo " $EbsIo1StorageSizePercentUsed > $warningLimit" | bc) -eq 1 ]] ||
  [[ $(echo " $EbsProvisionedIopsPercentUsed > $warningLimit" | bc) -eq 1 ]] ||
  [[ $(echo " $Ec2OnDemandInstanceCountPercentUsed > $warningLimit" | bc) -eq 1 ]] ||
  [[ $(echo " $Ec2SpotInstanceCountPercentUsed > $warningLimit" | bc) -eq 1 ]] ||
  [[ $(echo " $Ec2ElasticIpCountPercentUsed > $warningLimit" | bc) -eq 1 ]] ||
  [[ $(echo " $Ec2ElasticLoadBalancerCountPercentUsed > $warningLimit" | bc) -eq 1 ]] ||
  [[ $(echo " $CfnStackCountPercentUsed > $warningLimit" | bc) -eq 1 ]] ||
  [[ $(echo " $AutoScalingGroupCountPercentUsed > $warningLimit" | bc) -eq 1 ]] ||
  [[ $(echo " $LaunchConfigurationCountPercentUsed > $warningLimit" | bc) -eq 1 ]] ||
  [[ $(echo " $RdsManualSnapshotsCountPercentUsed > $warningLimit" | bc) -eq 1 ]] ||
  [[ $(echo " $VpcCountPercentUsed > $warningLimit" | bc) -eq 1 ]]
  then
    echo "Using over $warningLimit% of a monitored AWS limit"
    statsd-client "my.aws.limits.error:1|g"
else
  echo "Using less than the warning level ($warningLimit%) of monitored AWS limits"
  statsd-client "my.aws.limits.error:0|g"
fi

