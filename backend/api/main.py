from fastapi import FastAPI
from core.config import settings
from contextlib import asynccontextmanager
from core.config import settings
from core.jobs import JobStatus, ProgressFn, job_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    job_manager.shutdown()   # stop worker threads when the server exits


app = FastAPI()

app.get("/health")
def health():
    return {
        "status": "ok",
        "workspace_dir": str(settings.workspace_dir),
        "max_index_workers": settings.max_index_workers
    }


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = job_manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/jobs")
def list_jobs():
    return job_manager.list()

