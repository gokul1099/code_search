from __future__ import annotations

import json

import numpy as np

from core.config import settings
from core.embedder import embed
from core.ingest import IngestError, collect_files, fetch_repo, repo_id_for
from core.parser import Chunk, parse_file


def _embedding_text(chunk: Chunk) -> str:
    # Path and name go in too, so queries like "login in auth" can match on them.
    return f"{chunk.path}\n{chunk.qualname}\n{chunk.code}"


def run_index(source: str) -> dict:
    """Fetch the repo, chunk every source file, embed the chunks, and save both to the repo folder."""
    repo_id = repo_id_for(source)
    root = fetch_repo(source, repo_id)

    files = collect_files(root)
    if not files:
        raise IngestError("No supported source files found")

    chunks = [chunk for path in files for chunk in parse_file(path, root)]
    if not chunks:
        raise IngestError("No code found to index")

    out = settings.workspace_dir / repo_id
    out.mkdir(parents=True, exist_ok=True)
    out_file = out / "chunks.json"
    out_file.write_text(json.dumps([c.to_dict() for c in chunks], indent=2))

    # Row i of vectors.npy is the embedding of chunks[i].
    vectors = embed([_embedding_text(c) for c in chunks])
    np.save(out / "vectors.npy", vectors)

    return {"repo_id": repo_id, "files": len(files), "chunks": len(chunks), "chunks_file": str(out_file)}
