#!/usr/bin/env python3
"""
Transcribe audio files using S3 and Consul callbacks.
This script takes input S3 path and output S3 path as arguments,
makes a request to the transcription service API,
waits for completion via Consul callback,
and reports success/failure with elapsed time.
"""

import argparse
import time
import uuid
from datetime import datetime
import boto3
import os
import sys
import json
import requests

# Adjust Python path to include src directory
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

# Import modules after adjusting path
from src.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, CONSUL_HOST, CONSUL_PORT
from src.s3 import download_file, upload_file
from src.jobs import create_job, get_job_status, update_job_status

def get_s3_client():
    """Initialize and return a boto3 S3 client."""
    try:
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION,
        )
        return s3_client
    except Exception as e:
        print(f"Failed to initialize S3 client: {e}")
        return None

def parse_s3_uri(s3_uri):
    """Parse S3 URI into bucket and key."""
    if not s3_uri.startswith("s3://"):
        raise ValueError("Invalid S3 URI. Must start with 's3://'")
    
    # Remove s3:// prefix
    s3_path = s3_uri[5:]
    
    # Split into bucket and key
    parts = s3_path.split("/", 1)
    if len(parts) != 2:
        raise ValueError("Invalid S3 URI format")
    
    bucket = parts[0]
    key = parts[1]
    
    return bucket, key

def normalize_service_url(service_url):
    """
    Normalize service URL to ensure proper format for HTTP requests.
    Handles cases where URL might include path components.
    """
    # Remove trailing slashes
    service_url = service_url.rstrip('/')
    
    # If no scheme is present, assume HTTP
    if not service_url.startswith(('http://', 'https://')):
        service_url = f"http://{service_url}"
    
    # Ensure the URL ends with /transcribe for proper API endpoint
    if not service_url.endswith('/transcribe'):
        if '/transcribe' not in service_url:
            service_url = f"{service_url}/transcribe"
    
    return service_url

def call_transcription_api(service_url, input_s3_path, output_s3_path, webhook_url=None, consul_key=None):
    """
    Call the transcription API endpoint to initiate a transcription job.
    """
    # Normalize the service URL
    normalized_url = normalize_service_url(service_url)
    url = f"{normalized_url}"
    
    payload = {
        "input_s3_path": input_s3_path,
        "output_s3_path": output_s3_path
    }
    
    # Add optional fields if provided
    if webhook_url:
        payload["webhook_url"] = webhook_url
    if consul_key:
        payload["consul_key"] = consul_key
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return response.json().get("job_id")
        else:
            print(f"Failed to initiate transcription: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Error calling transcription API: {e}")
        return None

def wait_for_job_completion(service_url, job_id, timeout=300):
    """
    Poll the service for job completion status.
    """
    # Normalize the service URL for status endpoint
    normalized_url = normalize_service_url(service_url)
    # Remove /transcribe from the URL to get base URL for status endpoint
    if normalized_url.endswith('/transcribe'):
        base_url = normalized_url[:-len('/transcribe')]
    else:
        base_url = normalized_url
    
    url = f"{base_url}/status/{job_id}"
    
    start_time = datetime.now()
    while (datetime.now() - start_time).seconds < timeout:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                
                if status == "completed":
                    return "completed", data.get("result")
                elif status == "failed":
                    return "failed", data.get("result")
            
            # Wait before polling again
            time.sleep(2)
        except Exception as e:
            print(f"Error polling job status: {e}")
            time.sleep(2)
    
    return "timeout", None

def main():
    parser = argparse.ArgumentParser(description="Transcribe audio file via service API")
    parser.add_argument("--service-url", required=True, help="URL of the transcription service (e.g., fabio.service.consul:9999)")
    parser.add_argument("--input-s3-path", required=True, help="Input S3 path (s3://bucket/key)")
    parser.add_argument("--output-s3-path", required=True, help="Output S3 path (s3://bucket/key)")
    parser.add_argument("--webhook-url", help="Webhook URL for notifications")
    parser.add_argument("--consul-key", help="Consul key for notifications")
    
    args = parser.parse_args()
    
    # Parse S3 URIs
    try:
        input_bucket, input_key = parse_s3_uri(args.input_s3_path)
        output_bucket, output_key = parse_s3_uri(args.output_s3_path)
    except ValueError as e:
        print(f"Error parsing S3 URIs: {e}")
        return 1
    
    # Normalize service URL for display
    normalized_service_url = normalize_service_url(args.service_url)
    
    # Initiate transcription via API
    print(f"Initiating transcription via service at {normalized_service_url}...")
    job_id = call_transcription_api(
        args.service_url, 
        args.input_s3_path, 
        args.output_s3_path,
        args.webhook_url,
        args.consul_key
    )
    
    if not job_id:
        print("Failed to initiate transcription job")
        return 1
    
    print(f"Started transcription job: {job_id}")
    
    # Wait for job completion
    start_time = datetime.now()
    print("Waiting for job completion...")
    
    status, result = wait_for_job_completion(args.service_url, job_id)
    
    end_time = datetime.now()
    elapsed_time = (end_time - start_time).total_seconds()
    
    if status == "completed":
        print("Transcription completed successfully!")
        print(f"Job ID: {job_id}")
        print(f"Elapsed time: {elapsed_time:.2f} seconds")
        if result:
            print(f"Result: {result}")
        return 0
    elif status == "failed":
        print("Transcription failed!")
        print(f"Job ID: {job_id}")
        print(f"Elapsed time: {elapsed_time:.2f} seconds")
        if result:
            print(f"Error details: {result}")
        return 1
    else:
        print("Transcription timed out!")
        print(f"Job ID: {job_id}")
        print(f"Elapsed time: {elapsed_time:.2f} seconds")
        return 1

if __name__ == "__main__":
    sys.exit(main())