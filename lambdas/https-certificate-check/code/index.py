#!/usr/bin/env python3

import argparse
import boto3
import datetime
import json, yaml
import logging
import os
import socket
import ssl
import sys
import urllib.request

# Logging: from https://docs.python.org/3/howto/logging-cookbook.html
# Lambda has read-only filesystem. So only create the filehandler when running locally (down in __main__.
logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])
logger.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.ERROR)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
# add the handlers to the logger



class ExpiredCertDetector(object):
    """
    Class to hold the logic for detecting expired HTTPS certificates.
    """

    def __init__(self, **kwargs):
        super(ExpiredCertDetector, self).__init__()
        self.expired_certs = set()
        self.expiring_certs = set()
        self.long_lasting_certs = set()
        self.unable_to_connect = set()
        self.buffer_days = int(os.environ['expiration_buffer'])
        self.hosts = set()

    def get_hosts(self):
        with urllib.request.urlopen(os.environ['hosts_url']) as url:
            data = url.read().decode()

        try:
            hosts = json.loads(data)['hosts']
        except json.decoder.JSONDecodeError:
            hosts = yaml.load(data)['hosts']

        self.hosts = set(hosts)

    def run(self):
        self.get_hosts()
        self.check_https_expiry_datetime()

    # Code basically taken from https://serverlesscode.com/post/ssl-expiration-alerts-with-lambda/
    def check_https_expiry_datetime(self):
        ssl_date_fmt = r'%b %d %H:%M:%S %Y %Z'

        context = ssl.create_default_context()

        for hostname in self.hosts:
            conn = context.wrap_socket(
                socket.socket(socket.AF_INET),
                server_hostname=hostname,
            )
            # 1 second timeout because Lambda has runtime limitations
            conn.settimeout(1.0)

            try:
                conn.connect((hostname, 443))
                ssl_info = conn.getpeercert()
                ssl_expiration_date = datetime.datetime.strptime(ssl_info['notAfter'], ssl_date_fmt)
                logger.debug("Host %s has certificate expiration of %s" % (hostname, ssl_expiration_date))

                if ssl_expiration_date < datetime.datetime.utcnow():
                    # already expired!
                    self.expired_certs.add(hostname)
                elif ssl_expiration_date < (datetime.datetime.utcnow() + datetime.timedelta(days=self.buffer_days)):
                    # going to expire in buffer
                    self.expiring_certs.add(hostname)
                else:
                    # expires after buffer days
                    self.long_lasting_certs.add(hostname)
            except:
                logger.warning("Failed to connect to %s" % hostname)
                self.unable_to_connect.add(hostname)
                pass


def report(detector_object):
    print("---------------")

    if len(detector_object.long_lasting_certs) > 0:
        expires_past_buffer_log = "Found {} hosts with certificate expiration dates beyond the {} day warning. Hosts: {}".format(
            len(detector_object.long_lasting_certs), detector_object.buffer_days, detector_object.long_lasting_certs
        )
        print(expires_past_buffer_log)

    if len(detector_object.expiring_certs) > 0:
        expires_soon_log = "Found {} hosts with certificate expiration dates within the {} day warning period. Hosts: {}".format(
            len(detector_object.expiring_certs), detector_object.buffer_days, detector_object.expiring_certs
        )
        print(expires_soon_log)

    if len(detector_object.expired_certs) > 0:
        expired_log = "Found {} hosts with already expired certificates!!! Hosts: {}".format(
            len(detector_object.expired_certs), detector_object.expired_certs
        )
        print(expired_log)

    if len(detector_object.unable_to_connect) > 0:
        connect_error_log = "Unable to connect to {} hosts!!! Hosts: {}".format(
            len(detector_object.unable_to_connect), detector_object.unable_to_connect
        )
        print(connect_error_log)

    print("---------------")


def send_sns(detector_object):
    if len(detector_object.expired_certs) > 0:
        message = "The following hosts were identified as having expired certs: {}".format(
            detector_object.expired_certs)

        boto3.client('sns').publish(
            TargetArn=os.environ['sns_topic_arn'],
            Message=message,
            Subject="Lambda Monitor: Expired HTTPS Certificates"
        )

    if len(detector_object.expiring_certs) > 0:
        message = "The following hosts were identified as having certs that will expire soon: {}".format(
            detector_object.expiring_certs)

        boto3.client('sns').publish(
            TargetArn=os.environ['sns_topic_arn'],
            Message=message,
            Subject="Lambda Monitor: Expiring HTTPS Certificates"
        )

    if len(detector_object.unable_to_connect) > 0:
        message = "Unable to connect to the following hosts: {}".format(detector_object.unable_to_connect)

        boto3.client('sns').publish(
            TargetArn=os.environ['sns_topic_arn'],
            Message=message,
            Subject="Lambda Monitor: Unable to check HTTPS Certificates"
        )
    print("foo")


def lambda_handler(event, context):
    detector = ExpiredCertDetector()
    detector.run()
    send_sns(detector)


if __name__ == "__main__":
    # Uncomment following two lines if want to test/debug/run/emulate lambda
    # lambda_handler("foo", "bar")
    # sys.exit(0)

    parser = argparse.ArgumentParser(description="Check for expired or soon to be expiring HTTPS certificates")
    parser.add_argument(
        "-n", "--no-report", help="Skip showing report",
        action="store_true", default=False
    )
    args = parser.parse_args()

    # # Logging: from https://docs.python.org/3/howto/logging-cookbook.html
    # Lambda has read-only filesystem. So only create the filehandler when running locally.
    # create file handler which logs even debug messages
    fh = logging.FileHandler(os.path.splitext(os.path.basename(__file__))[0] + ".log")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    detector = ExpiredCertDetector()
    detector.run()

    if not args.no_report:
        report(detector)
