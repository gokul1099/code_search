from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path

import pathspec

from core.config import settings

GITHUB_RE = re.compile(r"^https://github\.com/[\w.-]+/[\w.-]+?(\.git)?/?$")

SKIP_DIRS = {
    ".git", "node_modules", "venv", ".venv", "env", "__pycache__",
    "dist", "build", ".mypy_cache", ".pytest_cache", ".tox", "site-packages",
}


class IngestError(ValueError):
    pass


def is_github_url(source: str) -> bool:
    return bool(GITHUB_RE.match(source.strip()))


def validate_source(source: str) -> None:
    """Fail fast (before a background job starts) if the source is neither a GitHub URL nor a folder."""
    if not is_github_url(source) and not Path(source).expanduser().is_dir():
        raise IngestError(f"Not a directory or GitHub URL: {source}")


def repo_id_for(source: str) -> str:
    key = source.strip().rstrip("/") if is_github_url(source) else str(Path(source).expanduser().resolve())
    return hashlib.sha1(key.encode()).hexdigest()[:12]


def fetch_repo(source: str, repo_id: str) -> Path:
    """Return a local folder with the code: clone GitHub URLs, use local folders as-is."""
    if not is_github_url(source):
        path = Path(source).expanduser().resolve()
        if not path.is_dir():
            raise IngestError(f"Not a directory or GitHub URL: {source}")
        return path

    dest = settings.workspace_dir / repo_id / "src"
    shutil.rmtree(dest, ignore_errors=True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["git", "clone", "--depth", "1", source.strip(), str(dest)],
        capture_output=True, text=True, timeout=settings.clone_timeout_s,
    )
    if result.returncode != 0:
        raise IngestError(f"git clone failed: {result.stderr.strip()}")
    return dest


def collect_files(root: Path) -> list[Path]:
    """Source files to index: right extension, outside skipped folders, not gitignored, not huge."""
    gitignore = root / ".gitignore"
    spec = (pathspec.PathSpec.from_lines("gitwildmatch", gitignore.read_text().splitlines())
            if gitignore.exists() else None)

    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]   # prune in place
        for name in filenames:
            path = Path(dirpath) / name
            if path.suffix not in settings.supported_extensions:
                continue
            if spec and spec.match_file(path.relative_to(root).as_posix()):
                continue
            if path.stat().st_size > settings.max_file_bytes:
                continue
            files.append(path)
    return sorted(files)
