from __future__ import annotations

import json

import numpy as np

from core.config import settings
from core.embedder import embed

# bge models are trained to expect this prefix on search queries (not on indexed passages).
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


def search(repo_id: str, query: str, k: int = 5) -> list[dict]:
    """Return the k chunks of an indexed repo that are most similar to the query."""
    folder = settings.workspace_dir / repo_id
    chunks = json.loads((folder / "chunks.json").read_text())   # FileNotFoundError if not indexed
    vectors = np.load(folder / "vectors.npy")

    scores = vectors @ embed([QUERY_PREFIX + query])[0]
    top = np.argsort(-scores)[:k]
    return [{"score": float(scores[i]), **chunks[i]} for i in top]
