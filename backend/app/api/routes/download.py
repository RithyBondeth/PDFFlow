import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, ExpiredError, NotFoundError
from app.db.session import get_db
from app.models.job import JobStatus
from app.services import jobs as job_service
from app.services import storage

router = APIRouter(tags=["download"])

_MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".zip": "application/zip",
    ".png": "image/png",
    ".jpg": "image/jpeg",
}


@router.get(
    "/download/{job_id}",
    summary="Download a completed job's result",
    responses={
        409: {"description": "Job has not finished"},
        410: {"description": "Expired"},
    },
)
def download(job_id: uuid.UUID, db: Session = Depends(get_db)) -> FileResponse:
    job = job_service.get_job(db, job_id)

    if job.status == JobStatus.failed:
        raise ConflictError("This job failed, so there is nothing to download.")
    if job.status != JobStatus.completed or not job.output_stored_name:
        raise ConflictError("This job is still processing.")
    if job.is_expired:
        raise ExpiredError("This result has expired and was deleted.")

    path = storage.open_for_read("processed", job.output_stored_name)
    if not path.exists():
        raise NotFoundError("This result is no longer available.")

    filename = job.output_filename or f"pdfflow-{job.operation}{path.suffix}"
    return FileResponse(
        path,
        media_type=_MEDIA_TYPES.get(path.suffix, "application/octet-stream"),
        # RFC 5987 form keeps non-ASCII names intact without letting the value
        # break out of the header.
        headers={
            "Content-Disposition": (
                f'attachment; filename="{_ascii(filename)}"; '
                f"filename*=UTF-8''{quote(filename)}"
            ),
            "Cache-Control": "no-store",
        },
    )


def _ascii(name: str) -> str:
    return name.encode("ascii", "replace").decode("ascii").replace('"', "'")
