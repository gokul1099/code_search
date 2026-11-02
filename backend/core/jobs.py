from __future__ import annotations
import threading
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Callable
from core.config import settings

class JobStatus(str, Enum):
    QUEUED = 'queued'
    RUNNING = 'running'
    DONE = 'done'
    FAILED = 'failed'


@dataclass
class Job:
    id: str
    repo_id: str
    source: str
    status: JobStatus = JobStatus.QUEUED
    state: str = 'queued'
    progress: float = 0.0
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        return self.status in (JobStatus.QUEUED, JobStatus.RUNNING)

ProgressFn = Callable[[str, float], None]

class JobManager:
    def __init__(self, max_workers: int):
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="indexer"
        )

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return replace(job) if job else None
    def list(self) -> list[Job]:
        with self._lock:
            jobs = [replace(j) for j in self._jobs.values()]
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)

    def active_job_for_replace(self, repo_id: str) -> Job | None:
        with self._lock:
            for job in self._jobs.values():
                if job.repo_id == repo_id and job.is_active:
                    return replace(job)

    def submit(self, repo_id: str, source: str, work: Callable[[ProgressFn], None]) -> tuple[Job, bool]:
        with self._lock:
            for job in self._jobs.values():
                if job.repo_id == repo_id and job.is_active:
                    return replace(job), False

            job = Job(id=uuid.uuid4().hex, repo_id=repo_id, source=source)
            self._jobs[job.id] = job
        self._executor.submit(self._run, job.id, work)
        return replace(job), True

    def _update(self, job_id:str, **changes) -> None:
        with self._lock:
            job = self._jobs[job_id]
            for key, value in changes.items():
                setattr(job, key, value)

    def _run(self, job_id: str, work: Callable[[ProgressFn], None]) -> None:
        self._update(job_id, status= JobStatus.RUNNING, stage="starting")

        def report(stage: str, progress: float) -> None:
            self._update(job_id, stage=stage, progress=max(0.0, min(progress, 1.0)))

        try:
            work(report)
            self._update(
                job_id,
                status=JobStatus.DONE,
                stage="done",
                progress=1.0,
                finished_at=datetime.now(timezone.utc),
            )
        except Exception as exc:
            traceback.print_exc()   # full trace in the server log
            self._update(
                job_id,
                status=JobStatus.FAILED,
                error=f"{type(exc).__name__}: {exc}",
                finished_at=datetime.now(timezone.utc),
            )

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

job_manager = JobManager(max_workers=settings.max_index_workers)