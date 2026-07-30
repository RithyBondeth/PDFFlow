import asyncio
import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas.job import JobCreate, JobOut, JobStatusOut
from app.services import events, operations
from app.services import jobs as job_service
from app.services.rate_limit import limiter
from app.worker.celery_app import celery_app

router = APIRouter(tags=["jobs"])


@router.get("/operations", summary="The tool catalog")
def list_operations() -> list[dict]:
    return [op.as_dict() for op in operations.CATALOG]


@router.post(
    "/jobs/create",
    response_model=JobOut,
    status_code=201,
    summary="Queue a processing job",
)
@limiter.limit(settings.rate_limit_jobs)
def create_job(
    request: Request, payload: JobCreate, db: Session = Depends(get_db)
) -> JobOut:
    job = job_service.create_job(
        db,
        operation_key=payload.operation,
        file_ids=payload.file_ids,
        options=payload.options,
    )
    celery_app.send_task("pdfflow.process_job", args=[str(job.id)], queue="pdf")
    return JobOut.model_validate(job)


@router.get("/jobs/{job_id}", response_model=JobOut, summary="Full job record")
def get_job(job_id: uuid.UUID, db: Session = Depends(get_db)) -> JobOut:
    return JobOut.model_validate(job_service.get_job(db, job_id))


@router.get(
    "/jobs/{job_id}/status",
    response_model=JobStatusOut,
    summary="Lightweight status, for polling clients",
)
def get_status(job_id: uuid.UUID, db: Session = Depends(get_db)) -> JobStatusOut:
    return JobStatusOut.model_validate(job_service.get_job(db, job_id))


@router.get(
    "/jobs/{job_id}/events",
    summary="Server-Sent Events stream of job progress",
    response_class=StreamingResponse,
)
async def stream_events(
    request: Request, job_id: uuid.UUID, db: Session = Depends(get_db)
) -> StreamingResponse:
    # 404/410 surfaces here rather than inside the stream body.
    job = job_service.get_job(db, job_id)

    async def publisher():
        # Replay current state first so a client that connects late — or after
        # a very fast job — still sees the terminal event.
        yield _frame(
            "job_progress",
            {
                "id": str(job.id),
                "status": job.status.value,
                "progress": job.progress,
                "stage": job.stage,
            },
        )
        replayed = events.last_event(job.id)
        if replayed:
            yield _frame(replayed["event"], replayed["data"])
            if replayed["event"] in {events.JOB_COMPLETED, events.JOB_FAILED}:
                return

        loop = asyncio.get_running_loop()
        stream = events.subscribe(job.id)
        try:
            while True:
                if await request.is_disconnected():
                    return
                message = await loop.run_in_executor(None, next, stream, None)
                if message is None:
                    yield ": keep-alive\n\n"
                    continue
                yield _frame(message["event"], message["data"])
                if message["event"] in {events.JOB_COMPLETED, events.JOB_FAILED}:
                    return
        finally:
            stream.close()

    return StreamingResponse(
        publisher(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # nginx must not buffer SSE
        },
    )


def _frame(event: str, data: dict) -> str:
    import json

    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"
