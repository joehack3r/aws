# Expired HTTPS Certificates
Ever have a HTTPS certificate expire without knowing about it? Ever rely on another site to have their certificate expire? Wish you had an easy way to detect and notify about certificates that are about to expire? Now you do!

# Directions
To create the Lambda, you will be creating a CloudFormation stack. This can be done by running the command below or clicking on the Launch Stack button. Running the command assumes the AWS CLI is installed and configured with a user that has sufficient permissions to create the necessary AWS resources.

```
AWS_ACCOUNT_ID=`aws sts get-caller-identity --output text --query 'Account'`
SNS_TOPIC=NotifyMe
aws cloudformation create-stack \
    --stack-name check-https-certificates-courtesy-JoeHack3r \
    --template-body file://./cloudformation.yaml \
    --parameters ParameterKey=NotificationArn,ParameterValue=arn:aws:sns:us-east-1:$AWS_ACCOUNT_ID:$SNS_TOPIC \
    --capabilities "CAPABILITY_IAM" \
    --region us-east-1
```

[![launch button](https://d2908q01vomqb2.cloudfront.net/1b6453892473a467d07372d45eb05abc2031647a/2017/08/17/2-launch.png)](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/new?stackName=check-https-certificates-courtesy-JoeHack3r&templateURL=https://s3.amazonaws.com/public-joehack3r-com/lambdas/https-certificate-check/cloudformation.yaml)

# Solution Details
The script is written in Python and can be run interactively or as a Lambda function. The CloudFormation stack creates a Lambda, IAM Role, and CloudWatch rule to trigger the Lambda everyday at 12 UTC.
