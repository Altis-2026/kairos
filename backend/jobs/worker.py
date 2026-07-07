import os

import ee
from dotenv import load_dotenv
from redis import Redis
from rq import Worker, Queue

load_dotenv()


def job_run_analysis(analysis_type: str, bbox: list, start_date: str, end_date: str):
    from api.analyze import run_analysis

    return run_analysis(analysis_type, bbox, start_date, end_date)


def main():
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project:
        raise SystemExit("GOOGLE_CLOUD_PROJECT not set in .env")
    ee.Initialize(project=project)
    print(f"Worker: GEE initialized for {project}")

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    conn = Redis.from_url(redis_url)
    worker = Worker([Queue("kairos", connection=conn)], connection=conn)
    print("Worker: listening on queue 'kairos'")
    worker.work()


if __name__ == "__main__":
    main()
