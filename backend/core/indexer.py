from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from core.config import settings
from core.ingest import collect_files, materialize
from core.jobs import ProgressFn


def repo_dir(repo_id: str) -> Path:
    return settings.workspace_dir / repo_id


def run_index(repo_id: str, source: str, report: ProgressFn) -> None:
    report("fetching source", 0.05)
    root = materialize(source, repo_id)

    report("collecting files", 0.10)
    files = collect_files(root)
    if not files:
        raise ValueError("No supported source files found")

    # Phases 4-8 (parse, link, summarize, store) will go here.

    report("writing manifest", 0.95)
    write_manifest(repo_id, source, root, files)


def write_manifest(repo_id: str, source: str, root: Path, files: list[Path]) -> None:
    out = repo_dir(repo_id)
    out.mkdir(parents=True, exist_ok=True)
    (out / "manifest.json").write_text(json.dumps({
        "repo_id": repo_id,
        "source": source,
        "root": str(root),
        "file_count": len(files),
        "files": [f.relative_to(root).as_posix() for f in files],
        "indexed_at": datetime.now(timezone.utc).isoformat(),
    }, indent=2))