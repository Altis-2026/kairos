from fastapi import APIRouter, HTTPException
from rq.job import Job

from jobs.queue import get_queue

router = APIRouter()


@router.get("/status/{job_id}")
def job_status(job_id: str):
    queue = get_queue()
    if queue is None:
        raise HTTPException(
            status_code=503,
            detail="Job queue unavailable. Redis is not running, so analyses "
            "are executing synchronously instead.",
        )
    try:
        job = Job.fetch(job_id, connection=queue.connection)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    status = job.get_status()
    if status == "finished":
        return {"job_id": job_id, "status": "complete", "result": job.result}
    if status == "failed":
        return {"job_id": job_id, "status": "failed", "error": str(job.exc_info or "Unknown error")}
    return {"job_id": job_id, "status": status, "result": None}
