#!/usr/bin/env python3
"""
Transcribe audio files using S3 and Consul callbacks.
This script takes input S3 path and output S3 path as arguments,
initiates transcription, waits for completion via Consul callback,
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
import threading
from queue import Queue

# Add src to Python path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, CONSUL_HOST, CONSUL_PORT
from s3 import download_file, upload_file
from jobs import create_job, get_job_status, update_job_status

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
        raise ValueError("Invalid S3 URI. Must start with ' s3://'")
    
    # Remove s3:// prefix
    s3_path = s3_uri[5:]
    
    # Split into bucket and key
    parts = s3_path.split("/", 1)
    if len(parts) != 2:
        raise ValueError("Invalid S3 URI format")
    
    bucket = parts[0]
    key = parts[1]
    
    return bucket, key

def wait_for_consul_callback(job_id, timeout=300):
    """
    Simulate waiting for a Consul callback.
    In a real implementation, this would:
    1. Register with Consul to listen for callbacks
    2. Wait for a callback with the job result
    3. Return success/failure status
    """
    print(f"Waiting for Consul callback for job {job_id} (timeout: {timeout}s)...")
    
    # Simulate waiting for callback
    start_time = datetime.now()
    while (datetime.now() - start_time).seconds < timeout:
        # Check if job status is updated (simulating callback)
        job = get_job_status(job_id)
        if job and job.get("status") in ["completed", "failed"]:
            return job["status"]
        
        # Sleep for a bit before checking again
        time.sleep(1)
    
    return "timeout"

def main():
    parser = argparse.ArgumentParser(description="Transcribe audio file from S3")
    parser.add_argument("--input-s3-path", required=True, help="Input S3 path (s3://bucket/key)")
    parser.add_argument("--output-s3-path", required=True, help="Output S3 path (s3://bucket/key)")
    
    args = parser.parse_args()
    
    # Parse S3 URIs
    try:
        input_bucket, input_key = parse_s3_uri(args.input_s3_path)
        output_bucket, output_key = parse_s3_uri(args.output_s3_path)
    except ValueError as e:
        print(f"Error parsing S3 URIs: {e}")
        return 1
    
    # Create temporary file for download
    temp_file = f"/tmp/{uuid.uuid4()}.audio"
    
    # Download file from S3
    print(f"Downloading audio file from {args.input_s3_path}...")
    s3_client = get_s3_client()
    if not s3_client:
        print("Failed to initialize S3 client")
        return 1
        
    if not download_file(input_bucket, input_key, temp_file):
        print("Failed to download audio file")
        return 1
    
    print("Audio file downloaded successfully")
    
    # Create job
    job_id = create_job()
    print(f"Created transcription job: {job_id}")
    
    # Simulate processing time
    start_time = datetime.now()
    print("Starting transcription process...")
    
    # In a real implementation, you would:
    # 1. Submit the job to a transcription service
    # 2. Wait for a Consul callback with the result
    # 3. Upload the result to S3
    
    # For demonstration, we'll simulate a successful transcription
    # In a real scenario, this would be replaced with actual transcription logic
    time.sleep(2)  # Simulate processing time
    
    # Simulate successful completion
    end_time = datetime.now()
    elapsed_time = (end_time - start_time).total_seconds()
    
    # Create a mock transcription result
    transcription_result = f"Mock transcription result for job {job_id}\nElapsed time: {elapsed_time:.2f} seconds\n\n"
    
    # Save result to temporary file
    result_file = f"/tmp/{uuid.uuid4()}.txt"
    with open(result_file, "w") as f:
        f.write(transcription_result)
    
    # Upload result to S3
    print(f"Uploading transcription result to {args.output_s3_path}...")
    if not upload_file(result_file, output_bucket, output_key):
        print("Failed to upload transcription result")
        return 1
    
    # Update job status
    update_job_status(job_id, "completed")
    
    print("Transcription completed successfully!")
    print(f"Job ID: {job_id}")
    print(f"Elapsed time: {elapsed_time:.2f} seconds")
    
    # Clean up temporary files
    try:
        os.remove(temp_file)
        os.remove(result_file)
    except OSError:
        pass
    
    return 0

if __name__ == "__main__":
    sys.exit(main())