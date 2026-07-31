import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ValidationError
from app.db.session import get_db
from app.models.file_record import FileRecord
from app.schemas.job import FileOut, UploadResponse
from app.services import operations, storage, validation
from app.services.rate_limit import limiter

router = APIRouter(tags=["upload"])
logger = logging.getLogger(__name__)


@router.post(
    "/upload",
    response_model=UploadResponse,
    summary="Upload one or more files into temporary storage",
    description=(
        "Files are stored under a generated UUID name and deleted automatically "
        "after the configured TTL. The response lists the tools that can act on "
        "what was uploaded."
    ),
)
@limiter.limit(settings.rate_limit_uploads)
async def upload(
    request: Request,
    response: Response,  # slowapi injects rate-limit headers into this
    db: Session = Depends(get_db),
    files: list[UploadFile] = File(...),
) -> UploadResponse:
    if not files:
        raise ValidationError("No file was provided.")
    if len(files) > settings.max_files_per_job:
        raise ValidationError(
            f"At most {settings.max_files_per_job} files can be uploaded at once."
        )

    expires_at = datetime.now(UTC) + timedelta(minutes=settings.file_ttl_minutes)
    saved: list[FileRecord] = []
    stored_names: list[str] = []

    try:
        for upload_file in files:
            header = await upload_file.read(validation.SNIFF_BYTES)
            kind = validation.classify(upload_file.filename, header)
            await upload_file.seek(0)

            stored_name, size = storage.save_stream(
                upload_file.file, extension=kind.extension
            )
            stored_names.append(stored_name)
            stored_path = storage.resolve("uploads", stored_name)
            page_count = None
            if kind.family == "pdf":
                try:
                    with stored_path.open("rb") as pdf:
                        reader = PdfReader(pdf, strict=False)
                        if reader.is_encrypted:
                            raise ValidationError(
                                "This PDF is password protected. Unlock it first."
                            )
                        page_count = len(reader.pages)
                except (PdfReadError, OSError) as exc:
                    raise ValidationError("This file is not a readable PDF.") from exc
                if page_count == 0:
                    raise ValidationError("This PDF has no pages.")
            elif kind.family == "office":
                validation.validate_office_document(stored_path, kind.extension)
            record = FileRecord(
                original_name=validation.safe_display_name(upload_file.filename),
                stored_name=stored_name,
                size=size,
                mime_type=kind.mime_type,
                page_count=page_count,
                expires_at=expires_at,
            )
            db.add(record)
            saved.append(record)
        db.commit()
    except Exception:
        db.rollback()
        for stored_name in stored_names:
            storage.delete("uploads", stored_name)
        raise

    for record in saved:
        db.refresh(record)

    families = {validation.family_of(record.mime_type) for record in saved}
    # Only offer tools that can actually run on this many files of this kind.
    available = [
        op.as_dict()
        for op in operations.CATALOG
        if families <= op.accepts
        and len(saved) >= op.min_files
        and (len(saved) == 1 or op.multi_file)
        and (
            op.key != "organize"
            or all(
                record.page_count is not None
                and record.page_count <= operations.MAX_ORGANIZED_PAGES
                for record in saved
            )
        )
    ]

    logger.info("files_uploaded", extra={"count": len(saved)})

    return UploadResponse(
        files=[
            FileOut(
                id=record.id,
                original_name=record.original_name,
                size=record.size,
                mime_type=record.mime_type,
                family=validation.family_of(record.mime_type),
                page_count=record.page_count,
                expires_at=record.expires_at,
            )
            for record in saved
        ],
        available_operations=available,
    )
