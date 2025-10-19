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
    Handles load balancer configurations where the URL contains both
    the load balancer endpoint and the service path.
    """
    # Remove trailing slashes
    service_url = service_url.rstrip('/')
    
    # If no scheme is present, assume HTTP
    if not service_url.startswith(('http://', 'https://')):
        service_url = f"http://{service_url}"
    
    # Handle the case where the URL contains both load balancer and service path
    # e.g., "fabio.service.consul:9999/transcribe" 
    # This should become "http://fabio.service.consul:9999/transcribe/transcribe"
    
    # Check if the URL already contains a path component
    if '/transcribe' in service_url:
        # If it already has /transcribe, we need to make sure it's at the right level
        # For example: "http://fabio.service.consul:9999/transcribe" 
        # Should become: "http://fabio.service.consul:9999/transcribe/transcribe"
        if service_url.endswith('/transcribe'):
            # Already ends with /transcribe, so we need to add another /transcribe
            # But we should only do this if it's not already a full endpoint
            pass
        elif service_url.endswith('/transcribe/'):
            # Already has the double transcribe path
            pass
        else:
            # If it's just "fabio.service.consul:9999/transcribe" without the trailing slash
            # We should treat it as a load balancer URL and add the service path
            if service_url.count('/transcribe') == 1:
                # This looks like a load balancer URL with a service path
                # We need to make sure we're pointing to the actual service endpoint
                # So "http://fabio.service.consul:9999/transcribe" becomes
                # "http://fabio.service.consul:9999/transcribe/transcribe"
                pass
    
    # For now, let's simplify the approach:
    # If the URL ends with /transcribe, we want to make sure it's a proper API endpoint
    # The service URL format is: <load_balancer>:<port>/<service_path>
    # The actual API endpoint should be: <load_balancer>:<port>/<service_path>/transcribe
    
    # If it's a simple URL like "fabio.service.consul:9999", we want to make it:
    # "http://fabio.service.consul:9999/transcribe/transcribe"
    
    # If it's already "fabio.service.consul:9999/transcribe", we want:
    # "http://fabio.service.consul:9999/transcribe/transcribe"
    
    # But we need to be careful about the structure
    if service_url.endswith('/transcribe'):
        # Already ends with /transcribe, so we shouldn't add another one
        pass
    elif service_url.endswith('/transcribe/'):
        # Already ends with /transcribe/, so we shouldn't add another one
        pass
    elif service_url.endswith('/transcribe/transcribe'):
        # Already has the double transcribe path
        pass
    else:
        # If it's just a host:port or host:port/path, we want to make sure it's a proper endpoint
        # For load balancer scenarios, we typically want to add /transcribe at the end
        if service_url.count('/') == 2 and service_url.startswith('http://'):
            # This looks like "http://host:port" - add /transcribe
            if not service_url.endswith('/'):
                service_url += '/transcribe'
        elif service_url.count('/') == 3 and service_url.startswith('http://'):
            # This looks like "http://host:port/path" - add /transcribe to the path
            if not service_url.endswith('/'):
                service_url += '/transcribe'
    
    return service_url

def call_transcription_api(service_url, input_s3_path, output_s3_path, webhook_url=None, consul_key=None, debug=False):
    """
    Call the transcription API endpoint to initiate a transcription job.
    """
    # Normalize the service URL
    normalized_url = normalize_service_url(service_url)
    
    # Special handling for load balancer URLs
    # If the URL contains a path that ends with /transcribe, we want to make sure
    # it points to the actual API endpoint
    if normalized_url.endswith('/transcribe'):
        # If it's already ending with /transcribe, we want to make sure it's
        # pointing to the actual API endpoint
        # For load balancer scenarios, we want to make sure we're hitting the right endpoint
        if normalized_url.count('/transcribe') == 1:
            # This is likely a load balancer URL that needs to be transformed
            # e.g., "http://fabio.service.consul:9999/transcribe" should become
            # "http://fabio.service.consul:9999/transcribe/transcribe"
            # But we need to be careful about the exact structure
            
            # Let's simplify this - if it's a load balancer URL with a path,
            # we want to make sure it's pointing to the actual service endpoint
            if normalized_url.count('/') == 3 and normalized_url.startswith('http://'):
                # This is likely "http://host:port/path" - we want to make it "http://host:port/path/transcribe"
                if not normalized_url.endswith('/'):
                    normalized_url += '/transcribe'
            elif normalized_url.count('/') == 2 and normalized_url.startswith('http://'):
                # This is likely "http://host:port" - we want to make it "http://host:port/transcribe"
                if not normalized_url.endswith('/'):
                    normalized_url += '/transcribe'
    
    # Final URL construction
    url = normalized_url
    
    # If the URL doesn't end with /transcribe, we need to add it
    if not url.endswith('/transcribe'):
        if url.endswith('/'):
            url += 'transcribe'
        else:
            url += '/transcribe'
    
    # Ensure we have a proper URL with protocol
    if not url.startswith(('http://', 'https://')):
        url = f"http://{url}"
    
    # Make sure we don't have double transcribe paths
    if url.endswith('/transcribe/transcribe'):
        # Remove the extra transcribe
        url = url[:-1]  # Remove the last character (the second /)
        url = url[:-1]  # Remove the second to last character (the second t)
        url = url[:-1]  # Remove the third to last character (the second r)
        url = url[:-1]  # Remove the fourth to last character (the second a)
        url = url[:-1]  # Remove the fifth to last character (the second n)
        url = url[:-1]  # Remove the sixth to last character (the second s)
        url = url[:-1]  # Remove the seventh to last character (the second c)
        url = url[:-1]  # Remove the eighth to last character (the second h)
        url = url[:-1]  # Remove the ninth to last character (the second e)
        url = url[:-1]  # Remove the tenth to last character (the second /)
        url = url + '/transcribe'
    
    if debug:
        print(f"DEBUG: Final URL: {url}")
    
    payload = {
        "input_s3_path": input_s3_path,
        "output_s3_path": output_s3_path
    }
    
    # Add optional fields if provided
    if webhook_url:
        payload["webhook_url"] = webhook_url
    if consul_key:
        payload["consul_key"] = consul_key
    
    if debug:
        print(f"DEBUG: Making POST request to {url}")
        print(f"DEBUG: Request payload: {payload}")
    
    try:
        response = requests.post(url, json=payload)
        if debug:
            print(f"DEBUG: Response status code: {response.status_code}")
            print(f"DEBUG: Response headers: {dict(response.headers)}")
            print(f"DEBUG: Response body: {response.text}")
        
        if response.status_code == 200:
            return response.json().get("job_id")
        else:
            print(f"Failed to initiate transcription: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Error calling transcription API: {e}")
        return None

def wait_for_job_completion(service_url, job_id, timeout=300, debug=False):
    """
    Poll the service for job completion status.
    """
    # Normalize the service URL for status endpoint
    normalized_url = normalize_service_url(service_url)
    
    # Special handling for load balancer URLs
    # If the URL ends with /transcribe, we want to remove that for the status endpoint
    if normalized_url.endswith('/transcribe'):
        # Remove the /transcribe part to get the base URL
        base_url = normalized_url[:-len('/transcribe')]
    else:
        base_url = normalized_url
    
    # Ensure base_url is properly formatted
    if base_url.endswith('/'):
        base_url = base_url[:-1]
    
    # Construct the status endpoint URL
    url = f"{base_url}/status/{job_id}"
    
    if debug:
        print(f"DEBUG: Polling status endpoint: {url}")
    
    start_time = datetime.now()
    while (datetime.now() - start_time).seconds < timeout:
        try:
            response = requests.get(url)
            if debug:
                print(f"DEBUG: Status poll response status code: {response.status_code}")
                if response.status_code != 200:
                    print(f"DEBUG: Status poll response body: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                
                if debug:
                    print(f"DEBUG: Job status: {status}")
                
                if status == "completed":
                    return "completed", data.get("result")
                elif status == "failed":
                    return "failed", data.get("result")
            
            # Wait before polling again
            time.sleep(2)
        except Exception as e:
            if debug:
                print(f"DEBUG: Error polling job status: {e}")
            time.sleep(2)
    
    return "timeout", None

def main():
    parser = argparse.ArgumentParser(description="Transcribe audio file via service API")
    parser.add_argument("--service-url", required=True, help="URL of the transcription service (e.g., fabio.service.consul:9999)")
    parser.add_argument("--input-s3-path", required=True, help="Input S3 path (s3://bucket/key)")
    parser.add_argument("--output-s3-path", required=True, help="Output S3 path (s3://bucket/key)")
    parser.add_argument("--webhook-url", help="Webhook URL for notifications")
    parser.add_argument("--consul-key", help="Consul key for notifications")
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug output")
    
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
        args.consul_key,
        args.debug
    )
    
    if not job_id:
        print("Failed to initiate transcription job")
        return 1
    
    print(f"Started transcription job: {job_id}")
    
    # Wait for job completion
    start_time = datetime.now()
    print("Waiting for job completion...")
    
    status, result = wait_for_job_completion(args.service_url, job_id, timeout=300, debug=args.debug)
    
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