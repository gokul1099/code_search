from fastapi import FastAPI
from backend.core.config import settings

app = FastAPI()

app.get("/health")
def health():
    return {
        "status": "ok",
        "workspace_dir": str(settings.workspace_dir),
        "max_index_workers": settings.max_index_workers
    }


