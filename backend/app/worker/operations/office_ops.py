"""Office document conversion through an isolated LibreOffice process."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from app.core.errors import ValidationError
from app.worker.operations import OperationContext, OperationResult, register

CONVERSION_TIMEOUT_SECONDS = 180


def _output_name(original_name: str) -> str:
    return f"{Path(original_name).stem or 'document'}.pdf"


@register("office_to_pdf")
def office_to_pdf(ctx: OperationContext) -> OperationResult:
    if len(ctx.inputs) != 1:
        raise ValidationError("Select one Office document to convert.")

    source = ctx.inputs[0]
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice is None:
        # This is a deployment fault, not a problem with the user's document.
        # Let the generic worker boundary log it and return its safe 500-style
        # job message rather than claiming the upload was invalid.
        raise RuntimeError("LibreOffice is not installed in the worker image")

    output = ctx.workdir / f"{source.stem}.pdf"
    profile = ctx.workdir / "libreoffice-profile"
    temporary = ctx.workdir / "libreoffice-tmp"
    profile.mkdir(mode=0o700)
    temporary.mkdir(mode=0o700)

    # Only generated server paths reach the process. In particular, the
    # user-supplied filename is never used as an argument. shell=False plus an
    # isolated profile avoids command injection and cross-job state sharing.
    command = [
        soffice,
        f"-env:UserInstallation={profile.as_uri()}",
        "--headless",
        "--nologo",
        "--nodefault",
        "--nolockcheck",
        "--nofirststartwizard",
        "--convert-to",
        "pdf",
        "--outdir",
        str(ctx.workdir),
        str(source),
    ]
    environment = {
        "HOME": str(profile),
        "LANG": "C.UTF-8",
        "PATH": os.defpath,
        "SAL_USE_VCLPLUGIN": "svp",
        "TMPDIR": str(temporary),
    }

    ctx.progress(45, "converting")
    try:
        completed = subprocess.run(  # noqa: S603 - fixed executable, shell disabled
            command,
            cwd=ctx.workdir,
            env=environment,
            capture_output=True,
            check=False,
            timeout=CONVERSION_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise ValidationError(
            "This Office document took too long to convert. Try a smaller file."
        ) from exc

    if completed.returncode != 0 or not output.is_file():
        raise ValidationError("This Office document could not be converted to PDF.")
    try:
        with output.open("rb") as result_file:
            is_pdf = output.stat().st_size > 5 and result_file.read(5) == b"%PDF-"
    except OSError as exc:
        raise ValidationError(
            "This Office document could not be converted to PDF."
        ) from exc
    if not is_pdf:
        output.unlink(missing_ok=True)
        raise ValidationError("This Office document could not be converted to PDF.")

    ctx.progress(90, "finishing")
    return OperationResult(
        output,
        _output_name(ctx.original_names[0]),
        {"sourceFormat": source.suffix.removeprefix(".").upper()},
    )
