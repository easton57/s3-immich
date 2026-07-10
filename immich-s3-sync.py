import json
import logging
import sys

import boto3
from botocore.exceptions import ClientError
import os
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

S3_BUCKET = os.environ.get('S3_BUCKET')
S3_ENDPOINT_URL = os.environ.get('S3_ENDPOINT_URL') or None


def get_s3_client():
    return boto3.client('s3', endpoint_url=S3_ENDPOINT_URL)


def upload_file(file_name, object_name=None, extra_args=None):
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """
    if object_name is None:
        object_name = os.path.basename(file_name)

    s3_client = get_s3_client()
    try:
        s3_client.upload_file(file_name, S3_BUCKET, object_name, ExtraArgs=extra_args)
        logging.info(f"Uploaded {file_name} -> s3://{S3_BUCKET}/{object_name}")
    except ClientError as e:
        logging.error(f"Failed to upload {file_name}: {e}")
        return False
    return True


def get_upload_dir():
    """Get and validate the UPLOAD_DIR environment variable.
    
    :return: Absolute path to upload directory, or None if invalid
    """
    upload_dir = os.environ.get('UPLOAD_DIR')
    if not upload_dir:
        logging.error('UPLOAD_DIR environment variable not set')
        return None
    
    upload_dir = os.path.abspath(upload_dir)
    if not os.path.isdir(upload_dir):
        logging.error(f'UPLOAD_DIR does not exist or is not a directory: {upload_dir}')
        return None
    
    return upload_dir


def get_object_name(file_path, upload_dir):
    """Get the S3 object name preserving folder structure.
    
    :param file_path: Absolute path to the file
    :param upload_dir: Absolute path to the upload directory
    :return: Object name relative to upload_dir
    """
    return os.path.relpath(file_path, upload_dir)


def list_files_from_upload_dir(upload_dir):
    """List all files from the upload directory.
    
    :param upload_dir: Absolute path to upload directory
    :return: List of file paths
    """
    files = []
    for root, _, filenames in os.walk(upload_dir):
        for filename in filenames:
            files.append(os.path.join(root, filename))

    return files


def list_files_in_bucket(bucket_name):
    """List all object keys in an S3 bucket.

    :param bucket_name: Name of the S3 bucket
    :return: Set of object keys
    """
    s3_client = get_s3_client()
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name)
        keys = set()
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    keys.add(obj['Key'])
        logging.info(f"Found {len(keys)} existing objects in bucket")
        return keys
    except ClientError as e:
        logging.error(f"Failed to list bucket contents: {e}")
        return set()


def validate_config():
    missing = [var for var in ('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'S3_BUCKET', 'UPLOAD_DIR')
               if not os.environ.get(var)]
    if missing:
        logging.error(f"Missing required environment variables: {', '.join(missing)}")
        return False
    if not os.environ.get('AWS_REGION') and not S3_ENDPOINT_URL:
        logging.error("Either AWS_REGION or S3_ENDPOINT_URL must be set")
        return False
    return True


def main():
    if not validate_config():
        sys.exit(1)

    extra_args = None
    extra_args_json = os.environ.get('EXTRA_ARGS')
    if extra_args_json:
        extra_args = json.loads(extra_args_json)

    versioning = os.environ.get('VERSIONING')

    upload_dir = get_upload_dir()
    if not upload_dir:
        sys.exit(1)

    files = list_files_from_upload_dir(upload_dir)
    if not files:
        logging.warning("No files found to upload")
        return

    if not versioning:
        logging.info("Versioning disabled — checking for existing files in S3 to skip duplicates")
        cloud_files = list_files_in_bucket(S3_BUCKET)
        if cloud_files:
            files_to_upload = []
            for file_path in files:
                object_name = get_object_name(file_path, upload_dir)
                if object_name not in cloud_files:
                    files_to_upload.append(file_path)
            skipped = len(files) - len(files_to_upload)
            if skipped:
                logging.info(f"Skipping {skipped} already-uploaded file(s)")
            files = files_to_upload
    else:
        logging.info("Versioning enabled — uploading all files regardless")

    if not files:
        logging.info("All files already uploaded, nothing to do")
        return

    logging.info(f"Uploading {len(files)} file(s)")
    successes = 0
    failures = 0
    for file_path in files:
        object_name = get_object_name(file_path, upload_dir)
        if upload_file(file_path, object_name=object_name, extra_args=extra_args):
            successes += 1
        else:
            failures += 1

    logging.info(f"Done — {successes} uploaded, {failures} failed")
    if failures:
        sys.exit(1)


if __name__ == '__main__':
    main()



