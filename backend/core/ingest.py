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

def is_github_url(source:str) -> bool:
    return bool(GITHUB_RE.match(source.strip()))

def make_repo_id(source: str) -> str:
    if is_github_url(source):
        key = source.strip().rstrip("/").removesuffix(".git").lower()
    else:
        key = str(Path(source).expanduser().resolve())
    return hashlib.sha1(key.encode()).hexdigest()[:12]


def validate_source(source: str) -> None:
    if is_github_url(source):
        return 
    path = Path(source).expanduser()
    if not path.is_dir():
        raise IngestError(f"Not a directory of Github URL: {source}")
    

def materialize(source: str, repo_id: str) -> Path:
    if not is_github_url(source):
        return Path(source).expanduser().resolve()

    dest = settings.workspace_dir / repo_id / 'src'
    if dest.exists():
        shutil.rmtree(dest)

    dest.parent.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        ['git', 'clone', '--depth', '1', source.strip(), str(dest)],
        capture_output=True,
        text=True,
        timeout=settings.clone_timeout_e
    )

    if result.returncode != 0:
        raise IngestError(f"git clone failed: {result.stderr.strip()}")
    return dest


def _load_gitignore(root: Path) -> pathspec.PathSpec | None:
    gi = root / ".gitignore"
    if not gi.exists():
        return None
    return pathspec.PathSpec.from_lines("gitwildmatch", gi.read_text().splitlines())

def collect_files(root: Path) -> list[Path]:
    spec = _load_gitignore(root)
    files: list[Path] = []

    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        rel_dir = current.relative_to(root)

        # Prune: editing dirnames in place stops os.walk from entering these dirs
        dirnames[:] = [
            d for d in dirnames
            if d not in SKIP_DIRS
            and not (spec and spec.match_file((rel_dir / d).as_posix() + "/"))
        ]

        for name in filenames:
            path = current / name
            rel = path.relative_to(root).as_posix()
            if path.suffix not in settings.supported_extensions:
                continue
            if spec and spec.match_file(rel):
                continue
            if path.stat().st_size > settings.max_file_bytes:
                continue
            files.append(path)

    return sorted(files)