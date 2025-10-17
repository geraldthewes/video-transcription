from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import os

from src.s3 import download_file, upload_file
from src.transcription import transcribe_audio
from src.jobs import create_job, get_job_status, update_job_status
from src.notifications import send_webhook_notification, send_consul_notification

app = FastAPI()

class TranscriptionRequest(BaseModel):
    input_s3_path: str
    output_s3_path: str
    webhook_url: str = None
    consul_key: str = None

def process_transcription(job_id: str, input_s3_path: str, output_s3_path: str, webhook_url: str = None, consul_key: str = None):
    """
    Downloads the audio file, transcribes it, and uploads the result.
    """
    input_bucket_name, input_object_name = input_s3_path.split("/", 1)
    output_bucket_name, output_object_name = output_s3_path.split("/", 1)
    
    local_audio_path = f"/tmp/{os.path.basename(input_object_name)}"
    
    if not download_file(input_bucket_name, input_object_name, local_audio_path):
        update_job_status(job_id, "failed", {"error": "Failed to download audio file."})
        return

    transcription_result = transcribe_audio(local_audio_path)
    
    local_transcription_path = f"/tmp/{os.path.basename(output_object_name)}"
    with open(local_transcription_path, "w") as f:
        f.write(transcription_result)

    if not upload_file(local_transcription_path, output_bucket_name, output_object_name):
        update_job_status(job_id, "failed", {"error": "Failed to upload transcription."})
        return

    update_job_status(job_id, "completed", {"output_s3_path": output_s3_path})

    if webhook_url:
        send_webhook_notification(webhook_url, {"job_id": job_id, "status": "completed", "output_s3_path": output_s3_path})
    
    if consul_key:
        send_consul_notification(consul_key, "completed")

    os.remove(local_audio_path)
    os.remove(local_transcription_path)

@app.post("/transcribe")
async def transcribe(request: TranscriptionRequest, background_tasks: BackgroundTasks):
    job_id = create_job()
    background_tasks.add_task(
        process_transcription,
        job_id,
        request.input_s3_path,
        request.output_s3_path,
        request.webhook_url,
        request.consul_key,
    )
    return {"job_id": job_id}

@app.get("/status/{job_id}")
async def status(job_id: str):
    return get_job_status(job_id)

@app.get("/health")
def health_check():
    return {"status": "ok"}