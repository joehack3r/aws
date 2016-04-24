#!/usr/bin/env python

import argparse
import boto3
import logging
import os

def genrateUrl(s3connection, bucket, key, ttl):
	return s3connection.generate_presigned_url(
		ClientMethod='get_object',
		Params={
			'Bucket': bucket,
			'Key': key
		},
		ExpiresIn=ttl
	)


def main():

	# Arguments
	parser = argparse.ArgumentParser(description='Generating Presigned URLs for S3 bucket')
	parser.add_argument('-b', '--bucket', action='store', metavar='<S3 Bucket>', nargs=1,
						dest='bucket', required=True,
						help='S3 buckets')
	parser.add_argument('-k', '--key', action='store', metavar='<S3 key>', nargs='*',
						dest='keys', required=False,
						help='S3 object key(s)')
	parser.add_argument('-t', '--ttl', action='store', metavar='<TTL>', nargs=1,
						dest='ttl', required=False, default=3600,
						help='How long, in seconds, the generated URL is valid')

	loglevel_group = parser.add_mutually_exclusive_group()
	loglevel_group.add_argument('-d', '--debug', action="store_const", dest="loglevel", const=logging.DEBUG,
								help="Set log level to debug",
								default=logging.INFO)
	loglevel_group.add_argument('-v', '--verbose', action="store_const", dest="loglevel", const=logging.INFO,
								help="Set log level to verbose")
	args = parser.parse_args()


	# Variables
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

	s3client = boto3.client('s3')
	if args.keys:
		for key in args.keys:
			if key.startswith("/"):
				key = key[1:]
			logger.debug("Generating URL for bucket: %s; key: %s; ttl: %s" % (args.bucket[0], key, args.ttl[0]))
			print(genrateUrl(s3client, args.bucket[0], key, args.ttl[0]))
			total_api_count += 1
	else:
		object_list = s3client.list_objects(Bucket=args.bucket[0], MaxKeys=1000)
		total_api_count += 1
		# "Do-While"
		if 'Contents' in object_list:
			for object in object_list['Contents']:
				key = object['Key']
				logger.debug("Key is: %s" % (key))
				if key.endswith("/"):
					logger.debug("Key is a directory... skipping.")
					next
				else:
					logger.debug("Generating URL for bucket: %s; key: %s; ttl: %s" % (args.bucket[0], key, args.ttl[0]))
					print(genrateUrl(s3client, args.bucket[0], key, args.ttl[0]))
					total_api_count += 1
			while object_list['IsTruncated']:
				object_list = s3client.list_objects(Bucket=args.bucket[0], MaxKeys=1000,
												Marker=object_list['Contents'][-1]['Key'])
				total_api_count += 1
				for object in object_list['Contents']:
					key = object['Key']
					logger.debug("Key is: %s" % (key))
					if key.endswith("/"):
						logger.debug("Key is a directory... skipping.")
						next
					else:
						logger.debug("Generating URL for bucket: %s; key: %s; ttl: %s" % (args.bucket[0], key, args.ttl[0]))
						print(genrateUrl(s3client, args.bucket[0], key, args.ttl[0]))
						total_api_count += 1

	logger.debug("Total number of API calls: %d" % (total_api_count))
	logger.debug("Finished script: " + str(os.path.basename(__file__)))

if __name__ == '__main__':
	main()
