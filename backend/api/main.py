import threading
import traceback

from fastapi import FastAPI, HTTPException

from api.models import AskRequest, IndexRequest
from core.answer import LLMNotConfigured, answer
from core.indexer import run_index
from core.ingest import IngestError, validate_source
from core.jobs import jobs
from core.search import search

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


def _run_index_job(job_id: str, source: str) -> None:
    try:
        result = run_index(source, lambda message, progress: jobs.log(job_id, message, progress))
        jobs.finish(job_id, result)
    except Exception as e:   # any failure is reported to the UI instead of silently dying
        traceback.print_exc()
        jobs.fail(job_id, str(e) or type(e).__name__)


@app.post("/repos", status_code=202)
def index_repo(req: IndexRequest):
    try:
        validate_source(req.source)
    except IngestError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Don't start a second job for a source that is already being indexed.
    existing = jobs.active_for(req.source)
    if existing:
        return {"job_id": existing["id"]}

    job = jobs.create(req.source)
    threading.Thread(target=_run_index_job, args=(job["id"], req.source), daemon=True).start()
    return {"job_id": job["id"]}


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = jobs.snapshot(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/repos/{repo_id}/search")
def search_repo(repo_id: str, q: str, k: int = 5):
    try:
        return search(repo_id, q, k)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Repo not indexed")


@app.post("/repos/{repo_id}/ask")
def ask_repo(repo_id: str, req: AskRequest):
    try:
        return answer(repo_id, req.question)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Repo not indexed")
    except LLMNotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e))
