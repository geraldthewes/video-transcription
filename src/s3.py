import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError
import logging
import os

from src.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_s3_client(endpoint_url=None):
    """Initializes and returns a boto3 S3 client."""
    try:
        # Use the provided endpoint URL or fall back to default S3
        if endpoint_url is None:
            endpoint_url = os.getenv("S3_ENDPOINT")
        
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION,
            endpoint_url=endpoint_url,
        )
        return s3_client
    except (NoCredentialsError, PartialCredentialsError):
        logger.error("AWS credentials not found.")
        return None

def download_file(bucket_name, object_name, file_name):
    """Downloads a file from an S3 bucket."""
    s3_client = get_s3_client()
    if s3_client:
        try:
            s3_client.download_file(bucket_name, object_name, file_name)
            logger.info(f"File {object_name} downloaded from bucket {bucket_name} to {file_name}.")
            return True
        except ClientError as e:
            logger.error(f"Failed to download file: {e}")
            return False
    return False

def upload_file(file_name, bucket_name, object_name=None):
    """Uploads a file to an S3 bucket."""
    if object_name is None:
        object_name = file_name

    s3_client = get_s3_client()
    if s3_client:
        try:
            s3_client.upload_file(file_name, bucket_name, object_name)
            logger.info(f"File {file_name} uploaded to bucket {bucket_name} as {object_name}.")
            return True
        except ClientError as e:
            logger.error(f"Failed to upload file: {e}")
            return False
    return False
