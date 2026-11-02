from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from core.config import settings
from core.ingest import collect_files, materialize
from core.jobs import ProgressFn
from core.parser import parse_file

def repo_dir(repo_id: str) -> Path:
    return settings.workspace_dir / repo_id


def run_index(repo_id: str, source: str, report: ProgressFn) -> None:
    report("fetching source", 0.05)
    root = materialize(source, repo_id)

    report("collecting files", 0.10)
    files = collect_files(root)
    if not files:
        raise ValueError("No supported source files found")

    chunks = []
    for i, path in enumerate(files):
        chunks.extend(parse_file(path, root))
        report(f"parsing ({i + 1}/{len(files)})", 0.10 + 0.50 * (i + 1) / len(files))

    # Temporary: dump chunks so you can inspect them. Phase 8 replaces this.
    out = repo_dir(repo_id)
    out.mkdir(parents=True, exist_ok=True)
    (out / "chunks.json").write_text(json.dumps([c.to_dict() for c in chunks], indent=2))

    report("writing manifest", 0.95)
    write_manifest(repo_id, source, root, files, chunks)


def write_manifest(repo_id, source, root, files, chunks) -> None:
    out = repo_dir(repo_id)
    out.mkdir(parents=True, exist_ok=True)
    errors = [c.path for c in chunks if c.parse_error]
    (out / "manifest.json").write_text(json.dumps({
        "repo_id": repo_id,
        "source": source,
        "root": str(root),
        "file_count": len(files),
        "chunk_count": len(chunks),
        "parse_errors": errors,
        "indexed_at": datetime.now(timezone.utc).isoformat(),
    }, indent=2))