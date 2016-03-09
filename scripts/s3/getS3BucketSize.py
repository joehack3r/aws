#!/usr/bin/env python

import argparse
import boto3
import logging
import os

def main():

	# Arguments
	parser = argparse.ArgumentParser(description='Go through S3 buckets to determine size')
	parser.add_argument('-b', '--buckets', action='store', metavar='<S3 Bucket>', nargs='+',
						dest='bucket_filter', required=False,
						help='Specific S3 buckets to check the size of')
	parser.add_argument('-d', '--debug', action="store_const", dest="loglevel", const=logging.DEBUG,
						help="Set log level to debug",
						default=logging.INFO)
	parser.add_argument('-v', '--verbose', action="store_const", dest="loglevel", const=logging.INFO,
						help="Set log level to verbose")
	args = parser.parse_args()

	# Variables
	total_bucket_size = 0
	total_object_count = 0
	bucket_size = 0
	object_count = 0
	total_api_count = 0

	# Logging
	logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])
	logger.setLevel(logging.DEBUG)
	# create file handler which logs even debug messages
	fh = logging.FileHandler(os.path.splitext(os.path.basename(__file__))[0] + ".log")
	fh.setLevel(logging.DEBUG)
	# create console handler with a higher log level
	ch = logging.StreamHandler()
	ch.setLevel(level=args.loglevel)
	# create formatter and add it to the handlers
	formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
	ch.setFormatter(formatter)
	fh.setFormatter(formatter)
	# add the handlers to logger
	logger.addHandler(ch)
	logger.addHandler(fh)


	# Main
	logger.debug("Starting script: " + str(os.path.basename(__file__)))
	logger.debug("Arguments are %s" % (args))

	s3client = boto3.client('s3', region_name = 'us-east-1')

	_all_buckets_list = s3client.list_buckets()['Buckets']
	total_api_count += 1

	for bucket in _all_buckets_list:
		bucket_api_count = 0
		if args.bucket_filter != None and bucket['Name'] not in args.bucket_filter:
			logger.debug("Skippig bucket due to filter: %s" % (bucket['Name']))
		else:
			logger.debug("Working on bucket: %s" % (bucket['Name']))
			bucket_region = s3client.get_bucket_location(Bucket=bucket['Name'])['LocationConstraint']
			bucket_api_count += 1
			# Recreate client for the proper region
			# https://github.com/boto/boto3/issues/145
			s3client = boto3.client('s3', region_name = bucket_region)
			# "Do-While"
			bucket_size = 0
			object_count = 0
			object_list = s3client.list_objects(Bucket=bucket['Name'], MaxKeys=1000)
			bucket_api_count += 1
			if 'Contents' in object_list:
				object_count += len(object_list['Contents'])
				for _object in object_list['Contents']:
					bucket_size += _object['Size']
				while object_list['IsTruncated']:
					object_list = s3client.list_objects(Bucket=bucket['Name'], MaxKeys=1000, Marker=object_list['Contents'][-1]['Key'])
					bucket_api_count += 1
					object_count += len(object_list['Contents'])    
					for _object in object_list['Contents']:
						bucket_size += _object['Size']
			logger.debug("Bucket %s has %s objects using %d B: %.1f KiB: %.1f MiB: %.1f GiB" % (bucket['Name'], object_count, bucket_size, bucket_size*1.0/1024, bucket_size*1.0/1024/1024, bucket_size*1.0/1024/1024/1024))
			total_bucket_size += bucket_size
			total_object_count += object_count
			total_api_count += bucket_api_count
			logger.debug("Bucket API calls: %d" % (bucket_api_count))
	logger.info("Bucket Totals: %s objects using %d B: %.1f KiB: %.1f MiB: %.1f GiB" % (total_object_count, total_bucket_size, total_bucket_size*1.0/1024, total_bucket_size*1.0/1024/1024, total_bucket_size*1.0/1024/1024/1024))
	print("Bucket Totals: %s objects using %d B: %.1f KiB: %.1f MiB: %.1f GiB" % (total_object_count, total_bucket_size, total_bucket_size*1.0/1024, total_bucket_size*1.0/1024/1024, total_bucket_size*1.0/1024/1024/1024))
	logger.debug("Total number of API calls: %d" % (total_api_count))
	logger.debug("Finished script: " + str(os.path.basename(__file__)))

if __name__ == '__main__':
	main()
