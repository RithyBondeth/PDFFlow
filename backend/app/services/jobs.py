"""Job lifecycle helpers shared by the API and the worker."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ExpiredError, NotFoundError, ValidationError
from app.core.time import ensure_utc
from app.core.time import now as utc_now
from app.models.file_record import FileRecord
from app.models.job import Job, JobStatus
from app.services import events, operations, validation


def _now() -> datetime:
    return utc_now()


def get_job(db: Session, job_id: uuid.UUID) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise NotFoundError("This job does not exist or has already been cleaned up.")
    if job.status == JobStatus.expired:
        raise ExpiredError("This job has expired and its files were deleted.")
    return job


def load_files(db: Session, file_ids: list[uuid.UUID]) -> list[FileRecord]:
    """Fetch the requested uploads, preserving the caller's ordering."""
    rows = db.scalars(
        select(FileRecord).where(
            FileRecord.id.in_(file_ids), FileRecord.deleted.is_(False)
        )
    ).all()
    by_id = {row.id: row for row in rows}
    missing = [fid for fid in file_ids if fid not in by_id]
    if missing:
        raise NotFoundError("One or more files have expired. Please upload again.")

    ordered = [by_id[fid] for fid in file_ids]
    for record in ordered:
        if ensure_utc(record.expires_at) <= _now():
            raise ExpiredError("One or more files have expired. Please upload again.")
        if record.job_id is not None:
            raise ValidationError("This file has already been used for a job.")
    return ordered


def create_job(
    db: Session,
    *,
    operation_key: str,
    file_ids: list[uuid.UUID],
    options: dict,
) -> Job:
    operation = operations.get(operation_key)
    if operation is None:
        raise ValidationError("Unknown operation.")
    if not operation.implemented:
        raise ValidationError("This tool is not available yet.")

    if len(file_ids) > settings.max_files_per_job:
        raise ValidationError(
            f"At most {settings.max_files_per_job} files can be processed at once."
        )
    if len(file_ids) > 1 and not operation.multi_file:
        raise ValidationError("This tool works on a single file.")
    if len(file_ids) < operation.min_files:
        raise ValidationError(
            f"{operation.name} needs at least {operation.min_files} files."
        )

    files = load_files(db, file_ids)
    for record in files:
        family = validation.family_of(record.mime_type)
        if family not in operation.accepts:
            raise ValidationError("This tool cannot process one of these files.")

    if operation.key == "organize":
        page_count = files[0].page_count
        if page_count is None:
            raise ValidationError("The page count for this PDF is not available.")
        operations.organization_plan(options.get("pages"), page_count)

    expires_at = _now() + timedelta(minutes=settings.file_ttl_minutes)
    job = Job(
        operation=operation.key,
        status=JobStatus.pending,
        progress=0,
        stage="queued",
        options=options,
        input_filename=files[0].original_name,
        expires_at=expires_at,
    )
    db.add(job)
    db.flush()

    for index, record in enumerate(files):
        record.job_id = job.id
        # `files` is already in the caller's order (load_files preserves it).
        # Pinning it here is what makes merge honour the order the user chose,
        # since the worker reads the files back through Job.files.
        record.position = index
        # Inputs live at least as long as the job they belong to.
        record.expires_at = expires_at

    db.commit()
    db.refresh(job)

    events.publish(job.id, events.JOB_CREATED, {"id": str(job.id), "status": "pending"})
    return job


def mark_processing(db: Session, job: Job) -> None:
    job.status = JobStatus.processing
    job.started_at = _now()
    update_progress(db, job, 10, "preparing")


def update_progress(db: Session, job: Job, progress: int, stage: str) -> None:
    job.progress = max(0, min(100, progress))
    job.stage = stage
    db.commit()
    events.publish(
        job.id,
        events.JOB_PROGRESS,
        {
            "id": str(job.id),
            "progress": job.progress,
            "stage": stage,
            "status": job.status.value,
        },
    )


def mark_completed(
    db: Session,
    job: Job,
    *,
    stored_name: str,
    output_filename: str,
    size: int,
    extra: dict | None = None,
) -> None:
    job.status = JobStatus.completed
    job.progress = 100
    job.stage = "completed"
    job.output_stored_name = stored_name
    job.output_filename = validation.safe_display_name(
        output_filename, fallback="result.pdf"
    )
    job.output_size = size
    job.completed_at = _now()
    if extra:
        job.options = {**job.options, "result": extra}
    db.commit()

    events.publish(
        job.id,
        events.JOB_COMPLETED,
        {
            "id": str(job.id),
            "status": "completed",
            "progress": 100,
            "outputFilename": job.output_filename,
            "outputSize": size,
            "downloadUrl": f"/api/download/{job.id}",
            **(extra or {}),
        },
    )


def mark_failed(db: Session, job: Job, message: str) -> None:
    """``message`` must be user-safe — callers translate internal exceptions."""
    job.status = JobStatus.failed
    job.stage = "failed"
    job.error_message = message
    job.completed_at = _now()
    db.commit()
    events.publish(
        job.id,
        events.JOB_FAILED,
        {"id": str(job.id), "status": "failed", "errorMessage": message},
    )
