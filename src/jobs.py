import uuid
from datetime import datetime, timedelta
import logging
import os

# Setup logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

jobs = {}

def create_job():
    """Creates a new job with a unique ID and processing status."""
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "processing",
        "created_at": datetime.utcnow(),
    }
    logger.info(f"JOB CREATED: Job ID={job_id}")
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
        logger.info(f"JOB STATUS UPDATE: Job ID={job_id}, Status={status}")
        return True
    return False

def cleanup_jobs():
    """Removes jobs older than 24 hours."""
    cutoff = datetime.utcnow() - timedelta(hours=24)
    for job_id, job in list(jobs.items()):
        if job["created_at"] < cutoff:
            del jobs[job_id]
            logger.info(f"JOB CLEANUP: Removed expired job ID={job_id}")
