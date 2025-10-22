from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import os
import logging
from datetime import datetime

from src.s3 import download_file, upload_file
from src.transcription import transcribe_audio
from src.jobs import create_job, get_job_status, update_job_status
from src.notifications import send_webhook_notification, send_consul_notification
from src.config import ROOT_PATH

# Configure the FastAPI app with proper path prefix for documentation
# Check if we're running behind a proxy/load balancer with a path prefix
root_path = ROOT_PATH
if root_path and not root_path.startswith("/"):
    root_path = "/" + root_path

from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import os
import logging
from datetime import datetime

from src.s3 import download_file, upload_file
from src.transcription import transcribe_audio
from src.jobs import create_job, get_job_status, update_job_status
from src.notifications import send_webhook_notification, send_consul_notification
from src.config import ROOT_PATH

# Configure the FastAPI app with proper path prefix for documentation
# Check if we're running behind a proxy/load balancer with a path prefix
root_path = ROOT_PATH
if root_path and not root_path.startswith("/"):
    root_path = "/" + root_path

app = FastAPI(
    title="Video Transcription Service",
    description="A service for transcribing video/audio files using Whisper ASR models.",
    version="1.0.0",
    # Set the root path to handle load balancer prefixes
    root_path=root_path,
    # Configure OpenAPI settings to work with path prefixes
    openapi_url="/openapi.json" if not root_path else f"{root_path}/openapi.json",
    docs_url="/docs" if not root_path else f"{root_path}/docs",
    redoc_url="/redoc" if not root_path else f"{root_path}/redoc",
)

# Setup logging with custom formatting
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configure specific loggers to avoid excessive botocore logs
logging.getLogger("botocore").setLevel(logging.WARNING)
logging.getLogger("boto3").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

class TranscriptionRequest(BaseModel):
    input_s3_path: str
    output_s3_path: str
    webhook_url: str = None
    consul_notification: bool = False

def process_transcription(job_id: str, input_s3_path: str, output_s3_path: str, webhook_url: str = None, consul_notification: bool = False):
    """
    Downloads the audio file, transcribes it, and uploads the result.
    """
    # Log request details
    start_time = datetime.now()
    logger.info(f"REQUEST: Job ID={job_id}, Input={input_s3_path}, Output={output_s3_path}")
    
    # Log webhook and consul information
    if webhook_url:
        logger.info(f"WEBHOOK: Job ID={job_id}, Webhook URL={webhook_url}")
    if consul_notification:
        # Generate the standardized key for Consul notification
        standardized_key = f"services/video-transcription/{job_id}"
        logger.info(f"CONSOLE: Job ID={job_id}, Consul Notification Enabled Key={standardized_key}")
    
    # Properly parse S3 URIs to extract bucket and key
    def parse_s3_uri(s3_uri):
        """Parse S3 URI into bucket and key."""
        if not s3_uri.startswith("s3://"):
            raise ValueError(f"Invalid S3 URI: {s3_uri}. Must start with 's3://'")
        
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
    
    try:
        # Parse S3 URIs
        input_bucket_name, input_object_name = parse_s3_uri(input_s3_path)
        output_bucket_name, output_object_name = parse_s3_uri(output_s3_path)
    except ValueError as e:
        logger.error(f"Failed to parse S3 URIs: {e}")
        update_job_status(job_id, "failed", {"error": f"Failed to parse S3 URIs: {str(e)}"})
        return
    
    # Log S3 file being processed
    if log_level == "DEBUG":
        logger.debug(f"DEBUG: Processing S3 file - Bucket: {input_bucket_name}, Object: {input_object_name}")
    
    local_audio_path = f"/tmp/{os.path.basename(input_object_name)}"
    local_transcription_path = f"/tmp/{os.path.basename(output_object_name)}"
    
    try:
        # Download audio file
        if not download_file(input_bucket_name, input_object_name, local_audio_path):
            update_job_status(job_id, "failed", {"error": "Failed to download audio file."})
            logger.error(f"ERROR: Failed to download audio file for job {job_id}")
            return

        # Log input when in debug mode
        if log_level == "DEBUG":
            logger.debug(f"DEBUG: Audio file downloaded - Local path: {local_audio_path}")
        
        # Transcribe audio
        transcription_result = transcribe_audio(local_audio_path)
        
        # Log output when in debug mode
        if log_level == "DEBUG":
            logger.debug(f"DEBUG: Transcription result length: {len(transcription_result)} characters")
        
        # Write transcription to local file
        with open(local_transcription_path, "w") as f:
            f.write(transcription_result)

        # Upload transcription
        if not upload_file(local_transcription_path, output_bucket_name, output_object_name):
            update_job_status(job_id, "failed", {"error": "Failed to upload transcription."})
            logger.error(f"ERROR: Failed to upload transcription for job {job_id}")
            return

        update_job_status(job_id, "completed", {"output_s3_path": output_s3_path})
        logger.info(f"STATUS: Job {job_id} completed successfully")

        if webhook_url:
            send_webhook_notification(webhook_url, {"job_id": job_id, "status": "completed", "output_s3_path": output_s3_path})
        
        # Send Consul notification if enabled
        if consul_notification:
            standardized_key = f"services/video-transcription/{job_id}"
            send_consul_notification(standardized_key, "completed")

        # Clean up temporary files
        os.remove(local_audio_path)
        os.remove(local_transcription_path)
        
        # Log duration
        duration = datetime.now() - start_time
        logger.info(f"DURATION: Job {job_id} took {duration.total_seconds():.2f} seconds")
    except Exception as e:
        # Handle any exceptions during the transcription process
        update_job_status(job_id, "failed", {"error": f"Job failed: {str(e)}"})
        logger.error(f"ERROR: Job failed for job {job_id}: {str(e)}")
        # Clean up temporary files if they exist
        try:
            if os.path.exists(local_audio_path):
                os.remove(local_audio_path)
            if os.path.exists(local_transcription_path):
                os.remove(local_transcription_path)
        except:
            pass

@app.post("/transcribe")
async def transcribe(request: TranscriptionRequest, background_tasks: BackgroundTasks):
    job_id = create_job()
    background_tasks.add_task(
        process_transcription,
        job_id,
        request.input_s3_path,
        request.output_s3_path,
        request.webhook_url,
        request.consul_notification,
    )
    # Return the standardized consul key for the client
    consul_key = f"services/video-transcription/{job_id}" if request.consul_notification else None
    return {"job_id": job_id, "consul_key": consul_key}

@app.get("/status/{job_id}")
async def status(job_id: str):
    return get_job_status(job_id)

@app.get("/health")
def health_check():
    return {"status": "ok"} = FastAPI(
    title="Video Transcription Service",
    description="A service for transcribing video/audio files using Whisper ASR models.",
    version="1.0.0",
    # Set the root path to handle load balancer prefixes
    root_path=root_path,
    # Configure OpenAPI settings to work with path prefixes
    openapi_url="/openapi.json" if not root_path else f"{root_path}/openapi.json",
    docs_url="/docs" if not root_path else f"{root_path}/docs",
    redoc_url="/redoc" if not root_path else f"{root_path}/redoc",
)

# Setup logging with custom formatting
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configure specific loggers to avoid excessive botocore logs
logging.getLogger("botocore").setLevel(logging.WARNING)
logging.getLogger("boto3").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

class TranscriptionRequest(BaseModel):
    input_s3_path: str
    output_s3_path: str
    webhook_url: str = None
    consul_notification: bool = False

def process_transcription(job_id: str, input_s3_path: str, output_s3_path: str, webhook_url: str = None, consul_notification: bool = False):
    """
    Downloads the audio file, transcribes it, and uploads the result.
    """
    # Log request details
    start_time = datetime.now()
    logger.info(f"REQUEST: Job ID={job_id}, Input={input_s3_path}, Output={output_s3_path}")
    
    # Log webhook and consul information
    if webhook_url:
        logger.info(f"WEBHOOK: Job ID={job_id}, Webhook URL={webhook_url}")
    if consul_notification:
        # Generate the standardized key for Consul notification
        standardized_key = f"services/video-transcription/{job_id}"
        logger.info(f"CONSOLE: Job ID={job_id}, Consul Notification Enabled Key={standardized_key}")
    
    # Properly parse S3 URIs to extract bucket and key
    def parse_s3_uri(s3_uri):
        """Parse S3 URI into bucket and key."""
        if not s3_uri.startswith("s3://"):
            raise ValueError(f"Invalid S3 URI: {s3_uri}. Must start with 's3://'")
        
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
    
    try:
        # Parse S3 URIs
        input_bucket_name, input_object_name = parse_s3_uri(input_s3_path)
        output_bucket_name, output_object_name = parse_s3_uri(output_s3_path)
    except ValueError as e:
        logger.error(f"Failed to parse S3 URIs: {e}")
        update_job_status(job_id, "failed", {"error": f"Failed to parse S3 URIs: {str(e)}"})
        return
    
    # Log S3 file being processed
    if log_level == "DEBUG":
        logger.debug(f"DEBUG: Processing S3 file - Bucket: {input_bucket_name}, Object: {input_object_name}")
    
    local_audio_path = f"/tmp/{os.path.basename(input_object_name)}"
    local_transcription_path = f"/tmp/{os.path.basename(output_object_name)}"
    
    try:
        # Download audio file
        if not download_file(input_bucket_name, input_object_name, local_audio_path):
            update_job_status(job_id, "failed", {"error": "Failed to download audio file."})
            logger.error(f"ERROR: Failed to download audio file for job {job_id}")
            return

        # Log input when in debug mode
        if log_level == "DEBUG":
            logger.debug(f"DEBUG: Audio file downloaded - Local path: {local_audio_path}")
        
        # Transcribe audio
        transcription_result = transcribe_audio(local_audio_path)
        
        # Log output when in debug mode
        if log_level == "DEBUG":
            logger.debug(f"DEBUG: Transcription result length: {len(transcription_result)} characters")
        
        # Write transcription to local file
        with open(local_transcription_path, "w") as f:
            f.write(transcription_result)

        # Upload transcription
        if not upload_file(local_transcription_path, output_bucket_name, output_object_name):
            update_job_status(job_id, "failed", {"error": "Failed to upload transcription."})
            logger.error(f"ERROR: Failed to upload transcription for job {job_id}")
            return

        update_job_status(job_id, "completed", {"output_s3_path": output_s3_path})
        logger.info(f"STATUS: Job {job_id} completed successfully")

        if webhook_url:
            send_webhook_notification(webhook_url, {"job_id": job_id, "status": "completed", "output_s3_path": output_s3_path})
        
        # Send Consul notification if enabled
        if consul_notification:
            standardized_key = f"services/video-transcription/{job_id}"
            send_consul_notification(standardized_key, "completed")

        # Clean up temporary files
        os.remove(local_audio_path)
        os.remove(local_transcription_path)
        
        # Log duration
        duration = datetime.now() - start_time
        logger.info(f"DURATION: Job {job_id} took {duration.total_seconds():.2f} seconds")
    except Exception as e:
        # Handle any exceptions during the transcription process
        update_job_status(job_id, "failed", {"error": f"Job failed: {str(e)}"})
        logger.error(f"ERROR: Job failed for job {job_id}: {str(e)}")
        # Clean up temporary files if they exist
        try:
            if os.path.exists(local_audio_path):
                os.remove(local_audio_path)
            if os.path.exists(local_transcription_path):
                os.remove(local_transcription_path)
        except:
            pass

@app.post("/transcribe")
async def transcribe(request: TranscriptionRequest, background_tasks: BackgroundTasks):
    job_id = create_job()
    background_tasks.add_task(
        process_transcription,
        job_id,
        request.input_s3_path,
        request.output_s3_path,
        request.webhook_url,
        request.consul_notification,
    )
    # Return the standardized consul key for the client
    consul_key = f"services/video-transcription/{job_id}" if request.consul_notification else None
    return {"job_id": job_id, "consul_key": consul_key}

@app.get("/status/{job_id}")
async def status(job_id: str):
    return get_job_status(job_id)

@app.get("/health")
def health_check():
    return {"status": "ok"}