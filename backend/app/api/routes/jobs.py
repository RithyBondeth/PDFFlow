import uuid

from fastapi import APIRouter, Depends, Request, Response
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
    request: Request,
    response: Response,  # slowapi injects rate-limit headers into this
    payload: JobCreate,
    db: Session = Depends(get_db),
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

    # Snapshot before streaming rather than reaching into `job` from inside the
    # generator. FastAPI closes a yield-dependency before the response body is
    # sent, so by then the session is gone and `job` is detached — today that
    # happens to work because every column is already loaded, but it puts a
    # DetachedInstanceError one added attribute away.
    opening = {
        "id": str(job.id),
        "status": job.status.value,
        "progress": job.progress,
        "stage": job.stage,
    }

    async def publisher():
        conn = events.async_client()
        try:
            # Replay current state first so a client that connects late — or
            # after a very fast job — still sees the terminal event.
            yield _frame("job_progress", opening)

            replayed = await events.last_event_async(conn, job_id)
            if replayed:
                yield _frame(replayed["event"], replayed["data"])
                if replayed["event"] in {events.JOB_COMPLETED, events.JOB_FAILED}:
                    return

            # Idling on the subscription parks a coroutine, not a thread: the
            # blocking client would have needed one executor worker per
            # connected browser, capping concurrent viewers at the pool size.
            async for message in events.subscribe_async(conn, job_id):
                if await request.is_disconnected():
                    return
                if message is None:
                    yield ": keep-alive\n\n"
                    continue
                yield _frame(message["event"], message["data"])
                if message["event"] in {events.JOB_COMPLETED, events.JOB_FAILED}:
                    return
        finally:
            await conn.aclose()

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
