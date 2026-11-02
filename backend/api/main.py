from fastapi import FastAPI, HTTPException
from core.config import settings
from contextlib import asynccontextmanager
from core.config import settings
from core.jobs import JobStatus, ProgressFn, job_manager

from core.indexer import run_index
from core.ingest import IngestError, make_repo_id, validate_source
from models import IndexRequest

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

@app.post("/repos", status_code=status.HTTP_202_ACCEPTED)
def index_repo(req: IndexRequest):
    try:
        validate_source(req.source)
    except IngestError as e:
        raise HTTPException(status_code=400, detail=str(e))

    repo_id = make_repo_id(req.source)
    job, created = job_manager.submit(
        repo_id=repo_id,
        source=req.source,
        work=lambda report: run_index(repo_id, req.source, report),
    )
    return {"job": job, "created": created}

