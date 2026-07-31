"""Core PDF operations.

pypdf handles page-level structure (merge, split, extract, rotate); PyMuPDF
handles rendering and rewriting for compression. Both are pure-Python-facing
libraries with no shell-out, so no user input ever reaches a command line.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import fitz  # PyMuPDF
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError

from app.core.errors import ValidationError
from app.services.operations import organization_plan
from app.worker.operations import OperationContext, OperationResult, register
from app.worker.operations.pageranges import parse as parse_pages


def _open(path: Path) -> PdfReader:
    try:
        reader = PdfReader(str(path), strict=False)
    except PdfReadError as exc:
        raise ValidationError("This file is not a readable PDF.") from exc
    if reader.is_encrypted:
        raise ValidationError("This PDF is password protected. Unlock it first.")
    if len(reader.pages) == 0:
        raise ValidationError("This PDF has no pages.")
    return reader


def _stem(name: str) -> str:
    return Path(name).stem or "document"


@register("merge")
def merge(ctx: OperationContext) -> OperationResult:
    if len(ctx.inputs) < 2:
        raise ValidationError("Select at least two PDFs to merge.")

    writer = PdfWriter()
    total = len(ctx.inputs)
    for index, path in enumerate(ctx.inputs):
        reader = _open(path)
        for page in reader.pages:
            writer.add_page(page)
        ctx.progress(30 + int(50 * (index + 1) / total), "merging")

    output = ctx.workdir / "merged.pdf"
    with output.open("wb") as fh:
        writer.write(fh)
    return OperationResult(
        output, "merged.pdf", {"pageCount": len(writer.pages), "fileCount": total}
    )


@register("extract_pages")
def extract_pages(ctx: OperationContext) -> OperationResult:
    reader = _open(ctx.inputs[0])
    indices = parse_pages(ctx.options.get("pages"), len(reader.pages))

    writer = PdfWriter()
    for index in indices:
        writer.add_page(reader.pages[index])
    ctx.progress(80, "writing")

    output = ctx.workdir / "extracted.pdf"
    with output.open("wb") as fh:
        writer.write(fh)
    name = f"{_stem(ctx.original_names[0])}-pages.pdf"
    return OperationResult(output, name, {"pageCount": len(indices)})


@register("rotate")
def rotate(ctx: OperationContext) -> OperationResult:
    angle = ctx.options.get("angle", 90)
    if angle not in (90, 180, 270):
        raise ValidationError("Rotation must be 90, 180 or 270 degrees.")

    reader = _open(ctx.inputs[0])
    targets = set(parse_pages(ctx.options.get("pages"), len(reader.pages)))

    writer = PdfWriter()
    for index, page in enumerate(reader.pages):
        if index in targets:
            page.rotate(angle)
        writer.add_page(page)
    ctx.progress(80, "writing")

    output = ctx.workdir / "rotated.pdf"
    with output.open("wb") as fh:
        writer.write(fh)
    name = f"{_stem(ctx.original_names[0])}-rotated.pdf"
    return OperationResult(output, name, {"rotatedPages": len(targets), "angle": angle})


@register("organize")
def organize(ctx: OperationContext) -> OperationResult:
    reader = _open(ctx.inputs[0])
    source_count = len(reader.pages)
    pages = organization_plan(ctx.options.get("pages"), source_count)

    writer = PdfWriter()
    for position, item in enumerate(pages, start=1):
        # PdfWriter clones the source page. Rotate that clone so duplicating one
        # source page with different rotations cannot mutate the later copies.
        writer.add_page(reader.pages[item["source"] - 1])
        if item["rotation"]:
            writer.pages[-1].rotate(item["rotation"])
        ctx.progress(30 + int(50 * position / len(pages)), "organizing")

    output = ctx.workdir / "organized.pdf"
    with output.open("wb") as fh:
        writer.write(fh)
    name = f"{_stem(ctx.original_names[0])}-organized.pdf"
    return OperationResult(
        output,
        name,
        {"pageCount": len(pages), "sourcePageCount": source_count},
    )


@register("split")
def split(ctx: OperationContext) -> OperationResult:
    reader = _open(ctx.inputs[0])
    page_count = len(reader.pages)
    mode = ctx.options.get("mode", "every_page")
    stem = _stem(ctx.original_names[0])

    if mode == "ranges":
        groups = _explicit_groups(ctx.options.get("ranges"), page_count)
    elif mode == "every_page":
        groups = [[index] for index in range(page_count)]
    else:
        raise ValidationError("Unknown split mode.")

    output = ctx.workdir / "split.zip"
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for position, indices in enumerate(groups, start=1):
            writer = PdfWriter()
            for index in indices:
                writer.add_page(reader.pages[index])
            part = ctx.workdir / f"part-{position}.pdf"
            with part.open("wb") as fh:
                writer.write(fh)
            archive.write(part, arcname=f"{stem}-{position}.pdf")
            part.unlink(missing_ok=True)
            ctx.progress(30 + int(60 * position / len(groups)), "splitting")

    return OperationResult(output, f"{stem}-split.zip", {"partCount": len(groups)})


def _explicit_groups(expression: str | None, page_count: int) -> list[list[int]]:
    """Each comma-separated token becomes its own output document."""
    if not expression or not expression.strip():
        raise ValidationError("Enter at least one page range, for example 1-3,5.")
    groups = [
        parse_pages(token, page_count) for token in expression.split(",") if token.strip()
    ]
    if not groups:
        raise ValidationError("Enter at least one page range, for example 1-3,5.")
    return groups


# Rendering DPI and JPEG quality per level. "high" trades visible sharpness for
# size; "low" is close to lossless for text documents.
_COMPRESSION = {
    "low": {"dpi": 150, "quality": 85},
    "medium": {"dpi": 120, "quality": 70},
    "high": {"dpi": 96, "quality": 55},
}


@register("compress")
def compress(ctx: OperationContext) -> OperationResult:
    level = str(ctx.options.get("level", "medium")).lower()
    profile = _COMPRESSION.get(level)
    if profile is None:
        raise ValidationError("Compression level must be low, medium or high.")

    source = ctx.inputs[0]
    original_size = source.stat().st_size
    output = ctx.workdir / "compressed.pdf"

    with fitz.open(source) as document:
        if document.is_encrypted:
            raise ValidationError("This PDF is password protected. Unlock it first.")

        # First pass: rewrite with object streams and deflate. For text-heavy
        # documents this alone is often a large win and keeps text selectable.
        document.save(
            output,
            garbage=4,
            deflate=True,
            deflate_images=True,
            deflate_fonts=True,
            clean=True,
        )
        ctx.progress(60, "optimizing")

        # Second pass, only if rewriting barely helped: re-encode the pages as
        # images. This loses selectable text, so it is a fallback rather than
        # the default path.
        if output.stat().st_size > original_size * 0.9 and level != "low":
            rasterized = _rasterize(document, ctx.workdir, profile)
            if rasterized.stat().st_size < output.stat().st_size:
                output.unlink(missing_ok=True)
                rasterized.replace(output)

    ctx.progress(90, "finishing")

    # Some documents — already-optimised or very small ones — come out larger
    # than they went in, because rewriting adds structural overhead. Handing
    # the user a bigger file from a tool called "compress" is worse than
    # doing nothing, so keep the original in that case.
    if output.stat().st_size >= original_size:
        output.unlink(missing_ok=True)
        output.write_bytes(source.read_bytes())

    final_size = output.stat().st_size
    saved = max(0.0, (1 - final_size / original_size) * 100) if original_size else 0.0
    name = f"{_stem(ctx.original_names[0])}-compressed.pdf"
    return OperationResult(
        output,
        name,
        {
            "originalSize": original_size,
            "compressedSize": final_size,
            "percentSaved": round(saved, 1),
            "alreadyOptimized": final_size >= original_size,
            "level": level,
        },
    )


def _rasterize(document: fitz.Document, workdir: Path, profile: dict) -> Path:
    target = workdir / "rasterized.pdf"
    with fitz.open() as out:
        for page in document:
            pixmap = page.get_pixmap(dpi=profile["dpi"])
            image = pixmap.tobytes("jpeg", jpg_quality=profile["quality"])
            new_page = out.new_page(width=page.rect.width, height=page.rect.height)
            new_page.insert_image(new_page.rect, stream=image)
        out.save(target, garbage=4, deflate=True)
    return target
