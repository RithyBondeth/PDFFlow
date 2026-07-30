"""Celery tasks: the generic job dispatcher and the cleanup sweep."""

from __future__ import annotations

import logging
import shutil
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy import select

from app.core.config import settings
from app.core.errors import PDFFlowError
from app.core.time import now as utc_now
from app.db.session import session_scope
from app.models.file_record import FileRecord
from app.models.job import Job, JobStatus
from app.services import jobs as job_service
from app.services import storage
from app.worker.celery_app import celery_app
from app.worker.operations import OperationContext, get_handler

logger = logging.getLogger(__name__)


@celery_app.task(name="pdfflow.process_job", bind=True, max_retries=0)
def process_job(self, job_id: str) -> dict:
    """Run one job. Every failure path ends with a user-safe message on the job
    row and a JOB_FAILED event, so the browser never hangs on a spinner."""
    with session_scope() as db:
        job = db.get(Job, uuid.UUID(job_id))
        if job is None:
            logger.warning("job_missing", extra={"job_id": job_id})
            return {"status": "missing"}
        if job.status != JobStatus.pending:
            # Late redelivery of an acked task — do not redo finished work.
            return {"status": job.status.value}
        if job.is_expired:
            job_service.mark_failed(db, job, "This job expired before it could run.")
            return {"status": "expired"}

        handler = get_handler(job.operation)
        if handler is None:
            job_service.mark_failed(db, job, "This tool is not available.")
            return {"status": "failed"}

        job_service.mark_processing(db, job)
        settings.ensure_directories()
        workdir = Path(tempfile.mkdtemp(prefix=f"job-{job.id.hex[:8]}-", dir="/tmp"))

        try:
            inputs = [
                storage.open_for_read("uploads", record.stored_name)
                for record in job.files
            ]
            names = [record.original_name for record in job.files]
            if not inputs:
                raise PDFFlowError("No input files were found for this job.")

            job_service.update_progress(db, job, 30, "preparing")

            context = OperationContext(
                job_id=str(job.id),
                inputs=inputs,
                original_names=names,
                options=dict(job.options or {}),
                progress=lambda pct, stage: job_service.update_progress(
                    db, job, pct, stage
                ),
                workdir=workdir,
            )
            result = handler(context)

            stored_name, size = storage.save_stream(
                result.path.open("rb"),
                extension=result.path.suffix,
                bucket="processed",
                # Results can legitimately exceed the upload ceiling (a merge of
                # several files), so allow generous headroom here.
                max_bytes=settings.max_upload_bytes * settings.max_files_per_job,
            )
            job_service.mark_completed(
                db,
                job,
                stored_name=stored_name,
                output_filename=result.filename,
                size=size,
                extra=result.metadata,
            )
            logger.info(
                "job_completed",
                extra={"job_id": job_id, "operation": job.operation, "size": size},
            )
            return {"status": "completed"}

        except PDFFlowError as exc:
            # Raised deliberately by validation/operation code: safe to show.
            job_service.mark_failed(db, job, exc.message)
            return {"status": "failed"}
        except SoftTimeLimitExceeded:
            job_service.mark_failed(
                db, job, "This document took too long to process. Try a smaller file."
            )
            return {"status": "failed"}
        except Exception:
            logger.exception("job_error", extra={"job_id": job_id})
            job_service.mark_failed(
                db, job, "We could not process this document. Please try again."
            )
            return {"status": "failed"}
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
            # Inputs are of no further use once the job is terminal.
            _purge_inputs(db, job)


def _purge_inputs(db, job: Job) -> None:
    for record in job.files:
        if not record.deleted and storage.delete("uploads", record.stored_name):
            record.deleted = True
    db.commit()


@celery_app.task(name="pdfflow.cleanup_expired")
def cleanup_expired() -> dict:
    """Delete everything past its TTL. Runs every 5 minutes via Celery beat.

    The database is the source of truth; a second sweep catches orphaned files
    that have no row at all (for instance after a crash mid-upload).
    """
    now = utc_now()
    removed_files = 0
    expired_jobs = 0

    with session_scope() as db:
        records = db.scalars(
            select(FileRecord).where(
                FileRecord.expires_at <= now, FileRecord.deleted.is_(False)
            )
        ).all()
        for record in records:
            if storage.delete("uploads", record.stored_name):
                removed_files += 1
            record.deleted = True

        jobs = db.scalars(
            select(Job).where(Job.expires_at <= now, Job.status != JobStatus.expired)
        ).all()
        for job in jobs:
            if job.output_stored_name:
                storage.delete("processed", job.output_stored_name)
                removed_files += 1
                job.output_stored_name = None
            job.status = JobStatus.expired
            job.stage = "expired"
            expired_jobs += 1

    orphans = _sweep_orphans(now)

    logger.info(
        "cleanup_completed",
        extra={
            "files_removed": removed_files,
            "jobs_expired": expired_jobs,
            "orphans_removed": orphans,
        },
    )
    return {
        "filesRemoved": removed_files,
        "jobsExpired": expired_jobs,
        "orphansRemoved": orphans,
    }


def _sweep_orphans(now: datetime) -> int:
    """Remove files on disk older than twice the TTL regardless of any row."""
    cutoff = now.timestamp() - (settings.file_ttl_minutes * 60 * 2)
    removed = 0
    for directory in (settings.upload_dir, settings.processed_dir):
        if not directory.exists():
            continue
        for path in directory.iterdir():
            try:
                if path.is_file() and path.stat().st_mtime < cutoff:
                    path.unlink(missing_ok=True)
                    removed += 1
            except OSError:
                logger.warning("orphan_sweep_failed")
    return removed
