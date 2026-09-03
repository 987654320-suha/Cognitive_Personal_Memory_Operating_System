# LOCATION: backend/app/services/job_service.py
"""
job_service.py
==============
In-memory job management service for asynchronous document upload and processing.
Tracks job status, current processing stage, timestamps, error states, and resulting memory IDs.
Thread-safe with automatic job pruning.
"""

from __future__ import annotations
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Dict, Optional, Any


@dataclass
class UploadJob:
    job_id: str
    filename: str
    status: str = "pending"          # pending | processing | completed | failed
    stage: str = "received"          # received | saved | extracting | chunking | embedding | saving_db | completed | failed
    message: str = "Job created"
    memory_id: Optional[int] = None
    memory: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_time: float = field(default_factory=time.time)
    processing_time: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id":          self.job_id,
            "filename":        self.filename,
            "status":          self.status,
            "stage":           self.stage,
            "message":         self.message,
            "memory_id":       self.memory_id,
            "memory":          self.memory,
            "error":           self.error,
            "created_at":      self.created_at,
            "updated_at":      self.updated_at,
            "processing_time": self.processing_time,
        }


class JobManager:
    """Thread-safe manager for upload jobs."""

    def __init__(self, max_retention_seconds: float = 7200.0):
        self._jobs: Dict[str, UploadJob] = {}
        self._lock = Lock()
        self._retention_seconds = max_retention_seconds

    def create_job(self, filename: str) -> UploadJob:
        with self._lock:
            self._prune_unlocked()
            job_id = str(uuid.uuid4())
            job = UploadJob(
                job_id=job_id,
                filename=filename,
                status="processing",
                stage="received",
                message="Document uploaded and processing started",
            )
            self._jobs[job_id] = job
            return job

    def update_job(
        self,
        job_id: str,
        status: Optional[str] = None,
        stage: Optional[str] = None,
        message: Optional[str] = None,
        memory_id: Optional[int] = None,
        memory: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        processing_time: Optional[float] = None,
    ) -> Optional[UploadJob]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None

            now_iso = datetime.now(timezone.utc).isoformat()
            job.updated_at = now_iso

            if status is not None:
                job.status = status
            if stage is not None:
                job.stage = stage
            if message is not None:
                job.message = message
            if memory_id is not None:
                job.memory_id = memory_id
            if memory is not None:
                job.memory = memory
            if error is not None:
                job.error = error
            if processing_time is not None:
                job.processing_time = processing_time

            return job

    def get_job(self, job_id: str) -> Optional[UploadJob]:
        with self._lock:
            return self._jobs.get(job_id)

    def _prune_unlocked(self):
        """Remove jobs older than the retention threshold."""
        now = time.time()
        expired = [
            jid for jid, j in self._jobs.items()
            if (now - j.created_time) > self._retention_seconds
        ]
        for jid in expired:
            del self._jobs[jid]


_job_manager: Optional[JobManager] = None


def get_job_manager() -> JobManager:
    """Returns the singleton JobManager."""
    global _job_manager
    if _job_manager is None:
        _job_manager = JobManager()
    return _job_manager
