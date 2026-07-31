"""Public error types.

Rule of the codebase: anything raised here is safe to show a user. Everything
else is caught at the edge, logged with its traceback, and replaced with a
generic message so that server paths, stack frames and temporary filenames
never leave the process.
"""

from __future__ import annotations

from fastapi import status


class PDFFlowError(Exception):
    """Base class for errors whose message is safe to return to the client."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ValidationError(PDFFlowError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "validation_error"


class FileTooLargeError(PDFFlowError):
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    code = "file_too_large"


class UnsupportedFileTypeError(PDFFlowError):
    status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    code = "unsupported_file_type"


class NotFoundError(PDFFlowError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ExpiredError(PDFFlowError):
    status_code = status.HTTP_410_GONE
    code = "expired"


class ConflictError(PDFFlowError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"
