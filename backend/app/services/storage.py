"""Temporary file storage.

Design rules, all enforced here rather than at call sites:

* Filenames on disk are ``<uuid4><ext>`` where ``ext`` comes from a fixed
  allow-list. Uploaded names are stored as metadata only.
* Every path handed back is resolved and checked to be inside the configured
  storage root, so a crafted ``stored_name`` cannot escape it.
* Writes are streamed with a hard byte ceiling, so a lying Content-Length
  cannot fill the disk.
"""

from __future__ import annotations

import logging
import os
import shutil
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import BinaryIO, Literal, cast

from app.core.config import settings
from app.core.errors import FileTooLargeError, NotFoundError, ValidationError

logger = logging.getLogger(__name__)

Bucket = Literal["uploads", "processed"]

_CHUNK = 1024 * 1024


def _bucket_dir(bucket: Bucket) -> Path:
    return settings.upload_dir if bucket == "uploads" else settings.processed_dir


def new_stored_name(extension: str) -> str:
    """Generate an unguessable on-disk name for the given extension."""
    ext = extension.lower()
    if not ext.startswith("."):
        ext = f".{ext}"
    if not ext[1:].isalnum() or len(ext) > 6:
        raise ValidationError("Unsupported file extension.")
    return f"{uuid.uuid4().hex}{ext}"


def resolve(bucket: Bucket, stored_name: str) -> Path:
    """Resolve ``stored_name`` inside ``bucket``, refusing anything that
    escapes the bucket directory."""
    if not stored_name or "/" in stored_name or "\\" in stored_name:
        raise ValidationError("Invalid file reference.")
    if stored_name in {".", ".."} or stored_name.startswith("."):
        raise ValidationError("Invalid file reference.")

    root = _bucket_dir(bucket).resolve()
    candidate = (root / stored_name).resolve()
    # Path.is_relative_to covers symlinked names too, because we resolved both.
    if not candidate.is_relative_to(root):
        logger.warning("path_traversal_blocked", extra={"bucket": bucket})
        raise ValidationError("Invalid file reference.")
    return candidate


def open_for_read(bucket: Bucket, stored_name: str) -> Path:
    path = resolve(bucket, stored_name)
    if not path.is_file():
        raise NotFoundError("This file is no longer available.")
    return path


def save_stream(
    source: BinaryIO | Iterator[bytes],
    *,
    extension: str,
    bucket: Bucket = "uploads",
    max_bytes: int | None = None,
) -> tuple[str, int]:
    """Stream ``source`` to disk. Returns ``(stored_name, size)``.

    Aborts and removes the partial file as soon as the size ceiling is passed.
    """
    limit = max_bytes if max_bytes is not None else settings.max_upload_bytes
    stored_name = new_stored_name(extension)
    path = resolve(bucket, stored_name)
    path.parent.mkdir(parents=True, exist_ok=True)

    chunks = _iter_chunks(source)
    written = 0
    try:
        # 0o600: only the service account can read temporary user documents.
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as fh:
            for chunk in chunks:
                written += len(chunk)
                if written > limit:
                    raise FileTooLargeError(
                        f"File exceeds the {limit // (1024 * 1024)} MB limit."
                    )
                fh.write(chunk)
    except Exception:
        path.unlink(missing_ok=True)
        raise

    if written == 0:
        path.unlink(missing_ok=True)
        raise ValidationError("The uploaded file is empty.")

    return stored_name, written


def _iter_chunks(source: BinaryIO | Iterator[bytes]) -> Iterator[bytes]:
    if hasattr(source, "read"):
        reader = cast(BinaryIO, source)
        while True:
            chunk = reader.read(_CHUNK)
            if not chunk:
                return
            yield chunk
    else:
        yield from cast(Iterator[bytes], source)


def delete(bucket: Bucket, stored_name: str) -> bool:
    """Best-effort delete. Never raises for a file that is already gone."""
    try:
        path = resolve(bucket, stored_name)
    except ValidationError:
        return False
    try:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
            return True
        path.unlink(missing_ok=True)
        return True
    except OSError:
        logger.exception("file_delete_failed", extra={"bucket": bucket})
        return False
