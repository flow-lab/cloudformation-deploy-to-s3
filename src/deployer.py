import os
import boto3
import mimetypes
import json
import requests
import subprocess
import tempfile
import pathlib
import shutil
import pathspec
import semver

s3 = boto3.resource('s3')

def resource_handler(event, context):
  print(event)
  try:
    dev_target_bucket = event['ResourceProperties']['DevTargetBucket']
    prod_target_bucket = event['ResourceProperties']['ProdTargetBucket']

    with open('cloudformation/git-tag') as f:
        git_tag = f.readline()

    try:
      ver = semver.parse(git_tag)
    except:
      ver = False

    build_src = os.path.join(os.getcwd(), 'build')
    acl = event['ResourceProperties']['Acl']
    cacheControlPolicies = event['ResourceProperties']['CacheControlPolicies']
    print(event['RequestType'])
    if event['RequestType'] == 'Create' or event['RequestType'] == 'Update':
      print('uploading dev')
      upload(build_src, dev_target_bucket, acl, cacheControlPolicies)

      if ver:
        print('uploading prod')
        upload(build_src, prod_target_bucket, acl, cacheControlPolicies)
    else:
      print('ignoring')

    send_result(event)

  except Exception as err:
    send_error(event, err)
  return event


def upload(build_src, target_bucket, acl, cacheControlPolicies):
  for folder, subs, files in os.walk(build_src):
    for filename in files:
        source_file_path = os.path.join(folder, filename)
        destination_s3_key = os.path.relpath(source_file_path, build_src)
        contentType, encoding = mimetypes.guess_type(source_file_path)
        if contentType is None:
          contentType = 'application/octet-stream'
        upload_file(source_file_path, target_bucket,
                    destination_s3_key, s3, acl, cacheControlPolicies, contentType)


def upload_file(source, bucket, key, s3lib, acl, cacheControlPolicies, contentType):
    print('uploading from {} {} {}'.format(source, bucket, key))
    cacheControl = get_cache_control(key, cacheControlPolicies)
    s3lib.Object(bucket, key).put(ACL=acl, Body=open(source, 'rb'),
                                  CacheControl=cacheControl, ContentType=contentType)

def get_cache_control(key, cacheControlPolicies):
    for policy in cacheControlPolicies:
      spec = pathspec.PathSpec.from_lines('gitwildmatch', policy['PathPattern'].split(','))
      if spec.match_file(key):
        return policy['CacheControl']

def send_result(event):
  response_body = json.dumps({
    'Status': 'SUCCESS',
    'PhysicalResourceId': get_physical_resource_id(event),
    'StackId': event['StackId'],
    'RequestId': event['RequestId'],
    'LogicalResourceId': event['LogicalResourceId']
  })
  print(response_body)
  requests.put(event['ResponseURL'], data=response_body)


def send_error(event, error):
  response_body = json.dumps({
    'Status': 'FAILED',
    'Reason': str(error),
    'PhysicalResourceId': get_physical_resource_id(event),
    'StackId': event['StackId'],
    'RequestId': event['RequestId'],
    'LogicalResourceId': event['LogicalResourceId']
  })
  print(response_body)
  requests.put(event['ResponseURL'], data=response_body)

def get_physical_resource_id(event):
  if 'PhysicalResourceId' in event.keys():
    return event['PhysicalResourceId']
  else:
    return event['RequestId']
