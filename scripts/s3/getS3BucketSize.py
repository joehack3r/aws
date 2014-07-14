#!/usr/bin/env python

import argparse
import boto

class S3BucketSize(object):
    def parse_cli_args(self):
        ''' Command line argument processing '''

        parser = argparse.ArgumentParser(description='Calcualte and report S3 bucket size')
        parser.add_argument('--buckets', action='store', nargs='+', metavar='<S3 Bucket Name>', dest='s3Buckets',
                           help='S3 bucket(s) to calculate size')
        self.args = parser.parse_args()

    def get_bucket_size(self):
        try:
            s3conn = boto.connect_s3()
        except boto.exception.BotoServerError, e:
            print e
            sys.exit(1)

        for bucket in self.args.s3Buckets:
            s3bucket = s3conn.get_bucket(bucket)
            size = 0
            for key in s3bucket.list():
                size += key.size
            print "%s:%d B:%.1f KiB:%.1f MiB:%.1f GiB" % (bucket, size, size*1.0/1024, size*1.0/1024/1024, size*1.0/1024/1024/1024)

    def __init__(self):
        self.parse_cli_args()
        self.get_bucket_size()

if __name__ == '__main__':
     S3BucketSize()
