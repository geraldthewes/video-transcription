import uuid
from datetime import datetime, timedelta

jobs = {}

def create_job():
    """Creates a new job with a unique ID and processing status."""
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "processing",
        "created_at": datetime.utcnow(),
    }
    return job_id

def get_job_status(job_id):
    """Retrieves the status of a job."""
    return jobs.get(job_id)

def update_job_status(job_id, status, result=None):
    """Updates the status of a job."""
    if job_id in jobs:
        jobs[job_id]["status"] = status
        if result:
            jobs[job_id]["result"] = result
        return True
    return False

def cleanup_jobs():
    """Removes jobs older than 24 hours."""
    cutoff = datetime.utcnow() - timedelta(hours=24)
    for job_id, job in list(jobs.items()):
        if job["created_at"] < cutoff:
            del jobs[job_id]
