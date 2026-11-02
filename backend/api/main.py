from fastapi import FastAPI, HTTPException

from api.models import IndexRequest
from core.indexer import run_index
from core.ingest import IngestError
from core.search import search

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/repos")
def index_repo(req: IndexRequest):
    try:
        return run_index(req.source)
    except IngestError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/repos/{repo_id}/search")
def search_repo(repo_id: str, q: str, k: int = 5):
    try:
        return search(repo_id, q, k)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Repo not indexed")
