#!/usr/bin/env python3

import argparse
import boto3
import botocore
import json
import logging
import os
import sys
import time
from urllib.parse import urlparse

cfn = boto3.client('cloudformation')


def add_dict_to_parameters(parameter_dict, current_parameters=None, multiple_parameter_values=None):
    if current_parameters is None:
        current_parameters = {}
    if multiple_parameter_values is None:
        multiple_parameter_values = {}
    logger.debug("add_dict_to_parameters - begin")
    logger.debug(str(parameter_dict))
    if 'ParameterKey' in parameter_dict:
        _parameter_key = parameter_dict['ParameterKey']
        _parameter_value = parameter_dict['ParameterValue']
    elif 'OutputKey' in parameter_dict:
        _parameter_key = parameter_dict['OutputKey']
        _parameter_value = parameter_dict['OutputValue']
    else:
        logger.critical("Unexpected dict format: " + str(parameter_dict))
        return ()

    if _parameter_key in multiple_parameter_values.keys():
        multiple_parameter_values[_parameter_key].append(_parameter_value)
        logger.warn("Key %s already identified as having multiple values: %s" % (
            _parameter_key, multiple_parameter_values[_parameter_key]))
    elif _parameter_key in current_parameters.keys() and _parameter_value != current_parameters[_parameter_key]:
        multiple_parameter_values[_parameter_key] = []
        multiple_parameter_values[_parameter_key].append(current_parameters[_parameter_key])  # store the first value
        multiple_parameter_values[_parameter_key].append(_parameter_value)  # store this value
        current_parameters.pop(_parameter_key, None)
        logger.warn("Key %s identified as having multiple values: %s" % (
            _parameter_key, multiple_parameter_values[_parameter_key]))
    elif _parameter_key in current_parameters.keys() and _parameter_value == current_parameters[_parameter_key]:
        logger.info("Key %s already exists with same value: %s" % (_parameter_key, _parameter_value))
    else:
        current_parameters[_parameter_key] = _parameter_value
    logger.debug("add_dict_to_parameters - done")
    return ()


def add_outputs_to_parameters(stack_name, parameter_values, multiple_parameter_values):
    logger.debug("add_outputs_to_parameters - begin")
    _describe_stacks = cfn.describe_stacks(StackName=stack_name)
    if 'Outputs' in _describe_stacks['Stacks'][0]:
        for parameter in _describe_stacks['Stacks'][0]['Outputs']:
            add_dict_to_parameters(parameter, parameter_values, multiple_parameter_values)
    logger.debug("add_outputs_to_parameters - done")


def get_completed_stacks():
    logger.debug("get_completed_stacks - begin")
    _cfn_good_completed_states = ['CREATE_COMPLETE', 'ROLLBACK_COMPLETE', 'UPDATE_COMPLETE', 'UPDATE_ROLLBACK_COMPLETE']
    _completed_stack_names = []

    # "Do-While"
    _complete_stacks = cfn.list_stacks(StackStatusFilter=_cfn_good_completed_states)
    for _stack in _complete_stacks['StackSummaries']:
        _completed_stack_names.append(_stack['StackName'])
    while 'NextToken' in _complete_stacks:
        _complete_stacks = cfn.list_stacks(StackStatusFilter=_cfn_good_completed_states,
                                           NextToken=_complete_stacks['NextToken'])
        for _stack in _complete_stacks['StackSummaries']:
            _completed_stack_names.append(_stack['StackName'])

    logger.debug("Completed Stacks: " + ', '.join(_completed_stack_names))
    logger.debug("get_completed_stacks - done")
    return _completed_stack_names


def get_active_stacks():
    logger.debug("get_active_stacks - begin")
    _cfn_active_states = ['CREATE_IN_PROGRESS', 'CREATE_FAILED', 'CREATE_COMPLETE', 'ROLLBACK_IN_PROGRESS',
                          'ROLLBACK_FAILED', 'ROLLBACK_COMPLETE', 'DELETE_IN_PROGRESS', 'DELETE_FAILED',
                          'UPDATE_IN_PROGRESS', 'UPDATE_COMPLETE_CLEANUP_IN_PROGRESS', 'UPDATE_COMPLETE',
                          'UPDATE_ROLLBACK_IN_PROGRESS', 'UPDATE_ROLLBACK_FAILED',
                          'UPDATE_ROLLBACK_COMPLETE_CLEANUP_IN_PROGRESS', 'UPDATE_ROLLBACK_COMPLETE']
    _active_stack_names = []

    # "Do-While"
    _active_stacks = cfn.list_stacks(StackStatusFilter=_cfn_active_states)
    for _stack in _active_stacks['StackSummaries']:
        _active_stack_names.append(_stack['StackName'])
    while 'NextToken' in _active_stacks:
        _active_stacks = cfn.list_stacks(StackStatusFilter=_cfn_active_states, NextToken=_active_stacks['NextToken'])
        for _stack in _active_stacks['StackSummaries']:
            _active_stack_names.append(_stack['StackName'])

    logger.debug("Active Stacks: " + ', '.join(_active_stack_names))
    logger.debug("get_active_stacks - done")
    return _active_stack_names


# Main

# Arguments
parser = argparse.ArgumentParser(description='Create, Read, Update, and Delete CloudFormation stacks')
parser.add_argument('-f', '--definition-file', action='store', dest='definition_file', required=False,
                    help='Definition file identifying stacks to create, read, update, and delete')
loglevel_group = parser.add_mutually_exclusive_group()
loglevel_group.add_argument('-d', '--debug', action="store_const", dest="loglevel", const=logging.DEBUG,
                            help="Set log level to debug",
                            default=logging.INFO)
loglevel_group.add_argument('-v', '--verbose', action="store_const", dest="loglevel", const=logging.INFO,
                            help="Set log level to verbose")
args = parser.parse_args()

# Initialize
with open(args.definition_file) as cd_file:
    product_definition = json.load(cd_file)

# Set up logging
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

logger.debug("Starting script: " + str(os.path.basename(__file__)))
logger.debug("Arguments are %s" % (args))

# Get CloudFormation Parameters
parameter_values = {}
multiple_parameter_values = {}

# Get CloudFormation Stacks
completed_stack_names = get_completed_stacks()
active_stack_names = get_active_stacks()

if 'Parameters' in product_definition:
    # Files
    if 'Files' in product_definition['Parameters']:
        for i in range(len(product_definition['Parameters']['Files'])):
            if len(product_definition['Parameters']['Files'][i]) != 1:
                logger.critical("Invalid format: Only one object (parameter file) allowed per array element.")
                sys.exit(1)
            for key in product_definition['Parameters']['Files'][i]:
                parameter_file_path = urlparse(
                    product_definition['Parameters']['Files'][i][key]['Properties']['Path']).path
                with open(os.path.expanduser(parameter_file_path)) as currentParameterFile:
                    for parameter in json.load(currentParameterFile):
                        add_dict_to_parameters(parameter, parameter_values, multiple_parameter_values)

    # Existing Stacks
    if 'ExistingStacks' in product_definition['Parameters']:
        for i in range(len(product_definition['Parameters']['ExistingStacks'])):
            if len(product_definition['Parameters']['ExistingStacks'][i]) != 1:
                logger.critical("Invalid format: Only one object (existing stack) allowed per array element.")
                sys.exit(1)
            for parameter_stack in product_definition['Parameters']['ExistingStacks'][i]:
                try:
                    existing_stack_description = cfn.describe_stacks(StackName=parameter_stack)
                except botocore.exceptions.ClientError as e:
                    if e.response['Error']['Code'] == 'ValidationError':
                        logger.error("Validation Error: " + e.response['Error']['Message'])
                    continue
                if 'Outputs' in existing_stack_description['Stacks'][0]:
                    for parameter in existing_stack_description['Stacks'][0]['Outputs']:
                        add_dict_to_parameters(parameter, parameter_values, multiple_parameter_values)

    # Key/Value Pairs
    if 'KeyValuePairs' in product_definition['Parameters']:
        for parameter in product_definition['Parameters']['KeyValuePairs']:
            add_dict_to_parameters(parameter, parameter_values, multiple_parameter_values)

# Create/update the stacks
if 'StacksToCreateOrUpdate' in product_definition:
    for stack in product_definition['StacksToCreateOrUpdate']:
        for stack_name in stack:
            logger.info("Working on creating/updating stack: %s" % stack_name)
            stack_parameters = []
            stack_missing_parameters = []
            template_file_name = urlparse(stack[stack_name]['Properties']['Template']).path

            # Read the file into a variable
            with open(os.path.expanduser(template_file_name), 'r') as f:
                template_body_string = f.read()
            # Convert to json taking extra step if file was .yml
            if template_file_name.endswith('.yml'):
                # template_body_json = json.loads(json.dumps(yaml.load(template_body_string), sort_keys=True, indent=2))
                template_body_json = yaml.load(template_body_string)
            else:
                template_body_json = json.loads(template_body_string)

            if 'Capabilities' in stack[stack_name]['Properties']:
                stack_capabilities = stack[stack_name]['Properties']['Capabilities']
            else:
                stack_capabilities = []

            if 'DisableRollback' in stack[stack_name]['Properties']:
                disable_rollback = stack[stack_name]['Properties']['DisableRollback']
            else:
                disable_rollback = False

            if 'Parameters' in template_body_json:
                for parameter in template_body_json['Parameters']:
                    if parameter in parameter_values.keys():
                        stack_parameters.append(
                            {'ParameterKey': parameter, 'ParameterValue': parameter_values[parameter]})
                    elif 'Default' in template_body_json['Parameters'][parameter]:
                        logger.debug("Using the default parameter value")
                        stack_parameters.append({'ParameterKey': parameter,
                                                 'ParameterValue': template_body_json['Parameters'][parameter][
                                                     'Default']})
                    else:
                        stack_missing_parameters.append(parameter)
            logger.debug("Parameter values: " + json.dumps(stack_parameters))
            if len(stack_missing_parameters) != 0:
                logger.critical("Missing parameters: " + ', '.join(stack_missing_parameters))
                exit(1)

            if stack_name in completed_stack_names:
                logger.info("Stack %s is in a completed state. Starting update." % stack_name)
                try:
                    response = cfn.update_stack(
                        StackName=stack_name,
                        TemplateBody=template_body_string,
                        Parameters=stack_parameters,
                        Capabilities=stack_capabilities
                    )
                except botocore.exceptions.ClientError as e:
                    if e.response['Error']['Message'] == 'No updates are to be performed.':
                        logger.info("No updates are to be performed.")
                    elif e.response['Error']['Code'] == 'ValidationError':
                        logger.critical("Validation error: " + e.response['Error']['Message'])
                        exit(1)
                    else:
                        logger.critical("Unexpected ClientError: " + e.response['Error']['Message'])
                        exit(1)

            elif stack_name in active_stack_names:
                logger.critical("Stack %s is active, but not in a completed state." % stack_name)
                exit(1)

            else:
                logger.info("Stack %s does not exist. Starting create." % stack_name)
                try:
                    response = cfn.create_stack(
                        StackName=stack_name,
                        TemplateBody=template_body_string,
                        Parameters=stack_parameters,
                        Capabilities=stack_capabilities,
                        DisableRollback=disable_rollback
                    )
                except botocore.exceptions.ClientError as e:
                    if e.response['Error']['Code'] == 'ValidationError':
                        logger.critical("Validation error: " + e.response['Error']['Message'])
                        exit(1)
                    else:
                        logger.critical("Unexpected ClientError: " + e.response['Error']['Message'])
                        exit(1)
                active_stack_names.append(stack_name)

        while True:
            stack_events = cfn.describe_stack_events(StackName=stack_name)
            stack_resource_type = stack_events['StackEvents'][0]['ResourceType']
            stack_resource_status = stack_events['StackEvents'][0]['ResourceStatus']
            if stack_resource_type == 'AWS::CloudFormation::Stack' \
                    and stack_resource_status in ['CREATE_COMPLETE', 'UPDATE_COMPLETE']:
                logger.info("Stack %s has been created/updated." % stack_name)
                if 'AddOutputsToParameters' in stack[stack_name]['Properties'] \
                        and stack[stack_name]['Properties']['AddOutputsToParameters'] == False:
                    logger.debug("Do not add stack outputs to parameters")
                    break
                else:
                    logger.debug("Add stack outputs to parameters")
                    add_outputs_to_parameters(stack_name, parameter_values, multiple_parameter_values)
                break
            elif stack_resource_type == 'AWS::CloudFormation::Stack' \
                    and stack_resource_status in ['CREATE_FAILED', 'ROLLBACK_FAILED', 'ROLLBACK_COMPLETE',
                                                  'UPDATE_ROLLBACK_FAILED', 'UPDATE_ROLLBACK_COMPLETE']:
                logger.critical("Stack failed to create or update.")
                exit(1)
            else:
                logger.debug("Waiting for stack to complete operations")
            time.sleep(5)

if 'StacksToDelete' in product_definition:
    for stack in product_definition['StacksToDelete']:
        for stack_name in stack:
            logger.info("Working on deleting stack: %s" % stack_name)
            if stack_name in active_stack_names or stack_name in completed_stack_names:
                logger.debug("Stack %s exists... sending delete command." % stack_name)
                try:
                    response = cfn.delete_stack(
                        StackName=stack_name
                    )
                except botocore.exceptions.ClientError as e:
                    logger.critical("Unexpected ClientError: " + e)
                    exit(1)
            else:
                logger.info("Stack %s does not exist." % stack_name)
                break

            while True:
                try:
                    stack_events = cfn.describe_stack_events(StackName=stack_name)
                    stack_resource_type = stack_events['StackEvents'][0]['ResourceType']
                    stack_resource_status = stack_events['StackEvents'][0]['ResourceStatus']
                    if stack_resource_type == 'AWS::CloudFormation::Stack' and stack_resource_status in [
                        'DELETE_COMPLETE']:
                        logger.debug("Stack deleted.")
                        break
                    elif stack_resource_type == 'AWS::CloudFormation::Stack' and stack_resource_status in [
                        'DELETE_FAILED']:
                        logger.critical("Stack failed to delete.")
                        exit(1)
                    else:
                        logger.debug("Waiting for stack to complete deleting")
                    time.sleep(5)
                except botocore.exceptions.ClientError as e:
                    if e.response['Error']['Code'] == 'ValidationError':
                        logger.info("Stack %s has been deleted." % stack_name)
                        break
                    else:
                        logger.critical("Unexpected ClientError: " + e)
                        exit(1)

logger.debug("Finished script: " + str(os.path.basename(__file__)))
