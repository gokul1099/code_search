from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone


class JobStore:
    """In-memory record of indexing jobs. The API reads snapshots while a worker thread writes."""

    def __init__(self):
        self._jobs: dict[str, dict] = {}
        self._lock = threading.Lock()

    def create(self, source: str) -> dict:
        job = {
            "id": uuid.uuid4().hex,
            "source": source,
            "status": "running",       # running | done | failed
            "stage": "Starting...",    # the latest step, shown as the headline
            "progress": 0.0,           # 0.0 to 1.0
            "events": [],              # full log: [{"time": ..., "message": ...}]
            "result": None,
            "error": None,
        }
        with self._lock:
            self._jobs[job["id"]] = job
        return self.snapshot(job["id"])

    def active_for(self, source: str) -> dict | None:
        with self._lock:
            for job in self._jobs.values():
                if job["source"] == source and job["status"] == "running":
                    return _copy(job)
        return None

    def log(self, job_id: str, message: str, progress: float) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job["stage"] = message
            job["progress"] = max(job["progress"], min(progress, 1.0))
            job["events"].append({"time": _now(), "message": message})

    def finish(self, job_id: str, result: dict) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.update(status="done", stage="Done", progress=1.0, result=result)
            job["events"].append({"time": _now(), "message": "Index ready"})

    def fail(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.update(status="failed", stage="Failed", error=error)
            job["events"].append({"time": _now(), "message": f"Failed: {error}"})

    def snapshot(self, job_id: str) -> dict | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return _copy(job) if job else None


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


def _copy(job: dict) -> dict:
    return {**job, "events": list(job["events"])}


jobs = JobStore()
