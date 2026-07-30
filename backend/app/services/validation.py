"""Upload validation: extension allow-list plus real content sniffing.

The declared ``Content-Type`` and the client-supplied filename are treated as
hints; the authoritative check is the file's own magic bytes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from app.core.errors import UnsupportedFileTypeError


@dataclass(frozen=True)
class FileKind:
    extension: str
    mime_type: str
    family: str  # "pdf" | "image" | "office"


_BY_EXTENSION: dict[str, FileKind] = {
    ".pdf": FileKind(".pdf", "application/pdf", "pdf"),
    ".jpg": FileKind(".jpg", "image/jpeg", "image"),
    ".jpeg": FileKind(".jpg", "image/jpeg", "image"),
    ".png": FileKind(".png", "image/png", "image"),
    ".webp": FileKind(".webp", "image/webp", "image"),
    ".docx": FileKind(
        ".docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "office",
    ),
    ".xlsx": FileKind(
        ".xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "office",
    ),
    ".pptx": FileKind(
        ".pptx",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "office",
    ),
}

# Enough bytes for every signature below.
SNIFF_BYTES = 32


def sniff(header: bytes) -> str | None:
    """Return a family name inferred from magic bytes, or None."""
    if header.startswith(b"%PDF-"):
        return "pdf"
    if header.startswith(b"\xff\xd8\xff"):
        return "image"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "image"
    if header[:2] == b"PK":
        # OOXML files are zip containers; the concrete type is settled by the
        # extension, which we have already checked against the allow-list.
        return "office"
    return None


def safe_display_name(filename: str | None, *, fallback: str = "document") -> str:
    """Strip any directory component and control characters from a name that
    will only ever be echoed back to the user."""
    if not filename:
        return fallback
    name = PurePosixPath(filename.replace("\\", "/")).name
    name = "".join(ch for ch in name if ch.isprintable() and ch not in '<>:"|?*')
    name = name.strip().lstrip(".")
    return name[:200] or fallback


def classify(
    filename: str | None, header: bytes, *, allowed: set[str] | None = None
) -> FileKind:
    """Validate an upload and return its canonical kind.

    ``allowed`` optionally restricts the accepted families (e.g. ``{"pdf"}``).
    """
    display = safe_display_name(filename)
    extension = PurePosixPath(display).suffix.lower()
    kind = _BY_EXTENSION.get(extension)
    if kind is None:
        raise UnsupportedFileTypeError(
            "Unsupported file type. Upload a PDF, image, or Office document."
        )

    detected = sniff(header)
    if detected is None or detected != kind.family:
        raise UnsupportedFileTypeError("This file's contents do not match its extension.")

    if allowed is not None and kind.family not in allowed:
        raise UnsupportedFileTypeError(
            f"This tool accepts {', '.join(sorted(allowed))} files."
        )
    return kind


def family_of(mime_type: str) -> str:
    """Map a stored MIME type back to its family.

    The inverse of :func:`classify`, used wherever a persisted ``FileRecord``
    needs to be matched against an operation's accepted inputs.
    """
    if mime_type == "application/pdf":
        return "pdf"
    if mime_type.startswith("image/"):
        return "image"
    return "office"
