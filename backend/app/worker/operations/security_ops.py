"""Password protection: encrypting a PDF and removing encryption from one.

The password arrives in ``ctx.options`` from the read-once secret hand-off
(see ``app.services.job_secrets``). It must not be logged, put in an error
message or returned in result metadata.
"""

from __future__ import annotations

import secrets
from pathlib import Path

from pypdf import PasswordType, PdfReader, PdfWriter
from pypdf.constants import UserAccessPermissions
from pypdf.errors import DependencyError, PdfReadError

from app.core.errors import ValidationError
from app.services.operations import document_password
from app.worker.operations import OperationContext, OperationResult, register
from app.worker.operations.pdf_ops import _open, _stem

_PRINT = UserAccessPermissions.PRINT | UserAccessPermissions.PRINT_TO_REPRESENTATION
_COPY = UserAccessPermissions.EXTRACT | UserAccessPermissions.EXTRACT_TEXT_AND_GRAPHICS


def _flag(options: dict, key: str) -> bool:
    value = options.get(key, True)
    if not isinstance(value, bool):
        raise ValidationError("Permission options must be true or false.")
    return value


@register("protect")
def protect(ctx: OperationContext) -> OperationResult:
    password = document_password(ctx.options.get("password"))
    allow_printing = _flag(ctx.options, "allowPrinting")
    allow_copying = _flag(ctx.options, "allowCopying")

    reader = _open(ctx.inputs[0])
    writer = PdfWriter(clone_from=reader)
    ctx.progress(50, "encrypting")

    permissions = UserAccessPermissions.all()
    if not allow_printing:
        permissions &= ~_PRINT
    if not allow_copying:
        permissions &= ~_COPY
    restricted = not (allow_printing and allow_copying)

    # Restrictions only mean something if the person opening the file does not
    # also hold the owner password, which grants every permission. A random
    # owner password nobody is told keeps them in force for readers that honour
    # them. Without restrictions there is nothing to protect, so it matches.
    owner_password = secrets.token_urlsafe(32) if restricted else password
    writer.encrypt(
        user_password=password,
        owner_password=owner_password,
        permissions_flag=permissions,
        algorithm="AES-256",
    )

    output = ctx.workdir / "protected.pdf"
    with output.open("wb") as fh:
        writer.write(fh)
    return OperationResult(
        output,
        f"{_stem(ctx.original_names[0])}-protected.pdf",
        {
            "encryption": "AES-256",
            "allowPrinting": allow_printing,
            "allowCopying": allow_copying,
        },
    )


@register("unlock")
def unlock(ctx: OperationContext) -> OperationResult:
    password = document_password(ctx.options.get("password"))
    source: Path = ctx.inputs[0]

    try:
        reader = PdfReader(str(source), strict=False)
    except PdfReadError as exc:
        raise ValidationError("This file is not a readable PDF.") from exc
    if not reader.is_encrypted:
        raise ValidationError("This PDF is not password protected.")

    try:
        result = reader.decrypt(password)
    except (DependencyError, NotImplementedError) as exc:
        raise ValidationError(
            "This PDF uses a kind of encryption PDFFlow cannot open."
        ) from exc
    if result == PasswordType.NOT_DECRYPTED:
        raise ValidationError("That password is not correct.")
    ctx.progress(50, "decrypting")

    writer = PdfWriter(clone_from=reader)
    if len(writer.pages) == 0:
        raise ValidationError("This PDF has no pages.")

    output = ctx.workdir / "unlocked.pdf"
    with output.open("wb") as fh:
        writer.write(fh)
    # A file this service protected comes back as "name-protected.pdf";
    # "name-unlocked.pdf" reads better than "name-protected-unlocked.pdf".
    stem = _stem(ctx.original_names[0]).removesuffix("-protected") or "document"
    return OperationResult(
        output,
        f"{stem}-unlocked.pdf",
        {"pageCount": len(writer.pages)},
    )
