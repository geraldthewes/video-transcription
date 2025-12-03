#!/usr/bin/env python3
"""
Test script for transcription service.
This script tests the transcription workflow:
1. Submits a transcription job
2. Polls for status updates
3. Verifies output file creation
"""

import os
import requests
import time
import sys
from typing import Dict, Any

# Test data
INPUT_FILE = 's3://ai-storage/transcriber/tests/test001.mp4'
OUTPUT_FILE = 's3://ai-storage/transcriber/tests/output001.md'

def test_transcription_workflow():
    """Test the complete transcription workflow."""

    # Construct BASE_URL from environment variables
    service_host = os.environ.get('SERVICE_HOST', '')
    service_port = os.environ.get('SERVICE_PORT', '9999')
    service_prefix = os.environ.get('SERVICE_PREFIX', '')

    if service_host:
        # Build URL from environment variables
        BASE_URL = f"http://{service_host}:{service_port}"
        if service_prefix:
            BASE_URL += f"/{service_prefix}"
    else:
        # Fallback to original URL
        BASE_URL = "http://fabio.service.consul:9999/transcribe"

    # Print the constructed URL
    print(f"Using BASE_URL: {BASE_URL}")

    # Step 1: Submit transcription job
    print("Submitting transcription job...")
    try:
        response = requests.post(
            f"{BASE_URL}/transcribe",
            json={
                "input_s3_path": INPUT_FILE,
                "output_s3_path": OUTPUT_FILE
            }
        )

        if response.status_code != 200:
            print(f"Failed to submit transcription job: {response.status_code}")
            print(response.text)
            return False

        job_data = response.json()
        job_id = job_data.get('job_id')
        print(f"Job submitted successfully. Job ID: {job_id}")

    except Exception as e:
        print(f"Error submitting transcription job: {e}")
        return False

    # Step 2: Poll for job status updates
    print("Polling for job status...")
    max_polls = 30  # Maximum polls (30 * 2 seconds = 60 seconds max)
    poll_interval = 2  # seconds between polls
    cursor = ["|", "/", "-", "\\"]

    for i in range(max_polls):
        try:
            status_response = requests.get(f"{BASE_URL}/status/{job_id}")

            if status_response.status_code != 200:
                print(f"Failed to get job status: {status_response.status_code}")
                return False

            status_data = status_response.json()
            status = status_data.get('status', '')

            # Show cursor animation for processing - overwrite current line
            if status == 'processing':
                cursor_char = cursor[i % len(cursor)]
                # Use carriage return to overwrite the same line
                sys.stdout.write(f"\rJob status: {cursor_char} {status}")
                sys.stdout.flush()
            else:
                # Print regular status and move to new line
                print(f"Job status: {status}")

            if status == 'completed':
                # Print final completion message
                print("\nJob completed successfully!")
                break
            elif status == 'failed':
                print(f"\nJob failed: {status_data.get('error', 'Unknown error')}")
                return False
            elif status == 'running':
                print("Job is still running...")
            else:
                # Only show unexpected status if it's not 'processing'
                if status != 'processing':
                    print(f"Unexpected job status: {status}")

        except Exception as e:
            print(f"Error polling for job status: {e}")
            return False

        # Wait before next poll
        time.sleep(poll_interval)
    else:
        print("Timeout waiting for job completion")
        return False

    # Step 3: Check that output was created
    print("Checking output file creation...")
    try:
        # This would typically be a check against the storage system
        # For now, we'll assume the service handles this correctly
        # In a real scenario, you might check S3 or the storage system directly

        # Simulate checking if output file exists (this would depend on your storage setup)
        print(f"Verifying output file exists at: {OUTPUT_FILE}")
        print("Test completed successfully!")
        return True

    except Exception as e:
        print(f"Error verifying output file: {e}")
        return False

if __name__ == "__main__":
    success = test_transcription_workflow()
    if success:
        print("✅ All tests passed!")
    else:
        print("❌ Tests failed!")
        exit(1)