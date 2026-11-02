from __future__ import annotations

import json
from collections.abc import Callable

import numpy as np

from core.config import settings
from core.embedder import embed
from core.ingest import IngestError, collect_files, fetch_repo, is_github_url, repo_id_for
from core.parser import Chunk, parse_file

EMBED_BATCH = 32   # chunks per embedding call, so progress moves during the slow step

Report = Callable[[str, float], None]   # (message, progress from 0.0 to 1.0)


def _embedding_text(chunk: Chunk) -> str:
    # Path and name go in too, so queries like "login in auth" can match on them.
    return f"{chunk.path}\n{chunk.qualname}\n{chunk.code}"


def run_index(source: str, report: Report = lambda message, progress: None) -> dict:
    """Fetch the repo, chunk every source file, embed the chunks, and save both to the repo folder."""
    repo_id = repo_id_for(source)

    if is_github_url(source):
        report("Cloning repository (large repos can take a minute)...", 0.02)
    root = fetch_repo(source, repo_id)
    report(f"Source ready: {root}", 0.08)

    files = collect_files(root)
    if not files:
        raise IngestError("No supported source files found")
    report(f"Found {len(files)} Python files", 0.10)

    chunks: list[Chunk] = []
    for i, path in enumerate(files, start=1):
        file_chunks = parse_file(path, root)
        chunks += file_chunks
        name = path.relative_to(root).as_posix()
        noun = "chunk" if len(file_chunks) == 1 else "chunks"
        report(f"Parsed {name} ({len(file_chunks)} {noun})", 0.10 + 0.60 * i / len(files))
    if not chunks:
        raise IngestError("No code found to index")
    report(f"Split code into {len(chunks)} chunks", 0.72)

    report("Loading embedding model (the first run downloads about 130 MB)...", 0.74)
    texts = [_embedding_text(c) for c in chunks]
    batches = []
    for start in range(0, len(texts), EMBED_BATCH):
        batch = texts[start:start + EMBED_BATCH]
        batches.append(embed(batch))
        done = start + len(batch)
        report(f"Embedded {done}/{len(texts)} chunks", 0.74 + 0.24 * done / len(texts))
    vectors = np.vstack(batches)

    # Write vectors before chunks: a repo counts as indexed only once chunks.json exists.
    out = settings.workspace_dir / repo_id
    out.mkdir(parents=True, exist_ok=True)
    np.save(out / "vectors.npy", vectors)
    out_file = out / "chunks.json"
    out_file.write_text(json.dumps([c.to_dict() for c in chunks], indent=2))
    report("Index saved", 1.0)

    return {"repo_id": repo_id, "files": len(files), "chunks": len(chunks)}
