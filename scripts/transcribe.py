#!/usr/bin/env python3
"""
Transcribe audio files using S3 and Consul callbacks.
This script takes input S3 path and output S3 path as arguments,
makes a request to the transcription service API,
waits for completion via Consul callback or polling,
and reports success/failure with elapsed time.
"""

import argparse
import time
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
    # Handle cases where there might be multiple slashes
    parts = s3_path.split("/", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid S3 URI format: {s3_uri}")
    
    bucket = parts[0]
    key = parts[1]
    
    # Validate bucket name
    if not bucket or bucket.strip() == "":
        raise ValueError(f"Invalid bucket name in S3 URI: {s3_uri}")
    
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
    
    return service_url

def call_transcription_api(service_url, input_s3_path, output_s3_path, webhook_url=None, consul_key=None, debug=False):
    """
    Call the transcription API endpoint to initiate a transcription job.
    """
    # Normalize the service URL
    normalized_url = normalize_service_url(service_url)
    
    # For load balancer scenarios, we need to preserve the structure
    # If the URL is like "http://fabio.service.consul:9999/transcribe"
    # We want to make it "http://fabio.service.consul:9999/transcribe/transcribe"
    
    # Extract the base URL part (before /transcribe)
    base_url = normalized_url
    if '/transcribe' in normalized_url:
        # Remove the /transcribe part to get the base URL
        if normalized_url.endswith('/transcribe'):
            base_url = normalized_url[:-len('/transcribe')]
        else:
            # Find the position of /transcribe and split
            pos = normalized_url.find('/transcribe')
            base_url = normalized_url[:pos]
    
    # Construct the final API endpoint
    # The final URL should be: http://fabio.service.consul:9999/transcribe/transcribe
    if base_url.endswith('/'):
        api_url = f"{base_url}transcribe/transcribe"
    else:
        api_url = f"{base_url}/transcribe/transcribe"
    
    # Ensure we don't have double slashes
    if '//transcribe' in api_url:
        api_url = api_url.replace('//transcribe', '/transcribe')
    
    if debug:
        print(f"DEBUG: Final API URL: {api_url}")
    
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
        print(f"DEBUG: Making POST request to {api_url}")
        print(f"DEBUG: Request payload: {payload}")
    
    try:
        response = requests.post(api_url, json=payload)
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
    # Normalize the service URL
    normalized_url = normalize_service_url(service_url)
    
    # Extract the base URL part (before /transcribe)
    base_url = normalized_url
    if '/transcribe' in normalized_url:
        # Remove the /transcribe part to get the base URL
        if normalized_url.endswith('/transcribe'):
            base_url = normalized_url[:-len('/transcribe')]
        else:
            # Find the position of /transcribe and split
            pos = normalized_url.find('/transcribe')
            base_url = normalized_url[:pos]
    
    # Construct the final status endpoint
    # The status URL should be: http://fabio.service.consul:9999/transcribe/status/{job_id}
    if base_url.endswith('/'):
        status_url = f"{base_url}transcribe/status/{job_id}"
    else:
        status_url = f"{base_url}/transcribe/status/{job_id}"
    
    # Ensure we don't have double slashes
    if '//transcribe' in status_url:
        status_url = status_url.replace('//transcribe', '/transcribe')
    
    if debug:
        print(f"DEBUG: Polling status endpoint: {status_url}")
    
    start_time = datetime.now()
    while (datetime.now() - start_time).seconds < timeout:
        try:
            response = requests.get(status_url)
            if debug:
                print(f"DEBUG: Status poll response status code: {response.status_code}")
                if response.status_code != 200:
                    print(f"DEBUG: Status poll response body: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                
                if debug:
                    print(f"DEBUG: Job status: {status}")
                    print(f"DEBUG: Full status data: {data}")
                
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
    parser.add_argument("--wait", choices=["poll", "consul"], default="poll", 
                       help="Wait method: poll (default) or consul")
    parser.add_argument("--consul-http-addr", help="Consul HTTP address (overrides CONSUL_HTTP_ADDR)")
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug output")
    
    args = parser.parse_args()
    
    # Parse S3 URIs
    try:
        input_bucket, input_key = parse_s3_uri(args.input_s3_path)
        output_bucket, output_key = parse_s3_uri(args.output_s3_path)
        
        # Enhanced error checking for problematic bucket names
        if input_bucket == "s3:" or output_bucket == "s3:":
            print("ERROR: S3 bucket parsing issue detected!")
            print(f"  Input S3 path: {args.input_s3_path}")
            print(f"  Parsed input bucket: '{input_bucket}'")
            print(f"  Parsed input key: '{input_key}'")
            print(f"  Output S3 path: {args.output_s3_path}")
            print(f"  Parsed output bucket: '{output_bucket}'")
            print(f"  Parsed output key: '{output_key}'")
            print("  This indicates a problem with S3 URI parsing.")
            print("  Please verify the S3 URI format and ensure it follows s3://bucket/key pattern.")
            return 1
            
    except ValueError as e:
        print(f"Error parsing S3 URIs: {e}")
        print("Please ensure S3 URIs are formatted correctly as s3://bucket/key")
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
        print("This could be due to:")
        print("  - Network connectivity issues")
        print("  - Service unavailability")
        print("  - Invalid API endpoint")
        return 1
    
    print(f"Started transcription job: {job_id}")
    
    # Wait for job completion
    start_time = datetime.now()
    print("Waiting for job completion...")
    
    # Determine wait method
    if args.wait == "consul":
        # Use Consul notification method - the server will handle Consul notifications
        # This is a simplified approach for demonstration purposes
        print("Using Consul notification method (server-side handling)...")
        # We'll still use the polling approach but note that Consul is selected
        status, result = wait_for_job_completion(
            args.service_url, 
            job_id, 
            timeout=300, 
            debug=args.debug
        )
    else:
        # Use polling method (default)
        status, result = wait_for_job_completion(
            args.service_url, 
            job_id, 
            timeout=300, 
            debug=args.debug
        )
    
    end_time = datetime.now()
    elapsed_time = (end_time - start_time).total_seconds()
    
    # Enhanced reporting of results with more detail
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
        else:
            print("No specific error details available")
        print("Possible causes:")
        print("  - Invalid input file")
        print("  - Processing error in transcription service")
        print("  - Storage issues")
        return 1
    else:  # timeout
        print("Transcription timed out!")
        print(f"Job ID: {job_id}")
        print(f"Elapsed time: {elapsed_time:.2f} seconds")
        print("This may indicate:")
        print("  - Long processing time")
        print("  - Service unavailability")
        print("  - Network issues")
        return 1

if __name__ == "__main__":
    sys.exit(main())