"""Conversions between PDFs and raster images.

PyMuPDF renders pages and lays out image pages; Pillow normalises uploaded
images (EXIF orientation, colour modes) and encodes WEBP. Neither shells out.
"""

from __future__ import annotations

import io
import math
import zipfile
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image, ImageOps

from app.core.errors import ValidationError
from app.services.validation import MAX_IMAGE_PIXELS
from app.worker.operations import OperationContext, OperationResult, register
from app.worker.operations.pageranges import parse as parse_pages

# --- images -> PDF -----------------------------------------------------

_PAGE_SIZES = {
    "a4": (595.28, 841.89),
    "letter": (612.0, 792.0),
}
# Margins in points: a quarter inch and half an inch.
_MARGINS = {"none": 0.0, "small": 18.0, "large": 36.0}
# PDF viewers are only required to support pages up to 200 inches a side.
_MAX_PAGE_POINTS = 14_400.0
# Used when an image carries no meaningful DPI. Cameras and phones almost
# always write a placeholder 72, which would turn a 4000px photo into a page
# over a metre wide, so only values at or above 96 (scanners, exports) are
# trusted.
_DEFAULT_IMAGE_DPI = 96.0
_MIN_TRUSTED_DPI = 96.0
_MAX_TRUSTED_DPI = 1200.0
# EXIF tag 0x0112. Anything other than 1 means the stored pixels are not upright.
_EXIF_ORIENTATION = 0x0112


def _stem(name: str) -> str:
    return Path(name).stem or "document"


def _image_dpi(image: Image.Image) -> float:
    dpi = image.info.get("dpi")
    try:
        value = float(dpi[0]) if dpi else 0.0
    except (TypeError, ValueError, IndexError):
        value = 0.0
    if _MIN_TRUSTED_DPI <= value <= _MAX_TRUSTED_DPI:
        return value
    return _DEFAULT_IMAGE_DPI


def _prepare_image(path: Path) -> tuple[bytes, int, int, float]:
    """Return encoded bytes MuPDF can embed, the upright pixel size and DPI.

    JPEGs that are already upright are embedded byte-for-byte: re-encoding
    them would only lose quality. Everything else is normalised through
    Pillow and stored as lossless PNG.
    """
    try:
        with Image.open(path) as image:
            width, height = image.size
            if width * height > MAX_IMAGE_PIXELS:
                raise ValidationError("One of these images is too large to process.")
            dpi = _image_dpi(image)
            orientation = image.getexif().get(_EXIF_ORIENTATION, 1)

            if image.format == "JPEG" and orientation == 1:
                return path.read_bytes(), width, height, dpi

            # Animated PNG/WEBP: the first frame is the image people expect.
            image.seek(0)
            upright = ImageOps.exif_transpose(image) or image
            if upright.mode not in {"1", "L", "LA", "RGB", "RGBA", "P"}:
                has_alpha = "A" in upright.getbands()
                upright = upright.convert("RGBA" if has_alpha else "RGB")
            buffer = io.BytesIO()
            upright.save(buffer, format="PNG")
            return buffer.getvalue(), upright.width, upright.height, dpi
    except ValidationError:
        raise
    except (OSError, SyntaxError, ValueError, Image.DecompressionBombError) as exc:
        raise ValidationError("One of these images could not be read.") from exc


def _layout(
    width: int, height: int, dpi: float, page_size: str, margin: float
) -> tuple[fitz.Rect, fitz.Rect]:
    """Return the page rectangle and the rectangle the image is drawn into."""
    natural_w = width * 72.0 / dpi
    natural_h = height * 72.0 / dpi

    if page_size == "fit":
        # Very large images are scaled to stay inside the PDF page limit.
        scale = min(
            1.0,
            (_MAX_PAGE_POINTS - 2 * margin) / natural_w,
            (_MAX_PAGE_POINTS - 2 * margin) / natural_h,
        )
        image_w, image_h = natural_w * scale, natural_h * scale
        page = fitz.Rect(0, 0, image_w + 2 * margin, image_h + 2 * margin)
        return page, fitz.Rect(margin, margin, margin + image_w, margin + image_h)

    short, long = _PAGE_SIZES[page_size]
    # Match the paper's orientation to the image's.
    page_w, page_h = (long, short) if width > height else (short, long)
    box_w, box_h = page_w - 2 * margin, page_h - 2 * margin
    scale = min(box_w / natural_w, box_h / natural_h)
    image_w, image_h = natural_w * scale, natural_h * scale
    left = (page_w - image_w) / 2
    top = (page_h - image_h) / 2
    return fitz.Rect(0, 0, page_w, page_h), fitz.Rect(
        left, top, left + image_w, top + image_h
    )


@register("images_to_pdf")
def images_to_pdf(ctx: OperationContext) -> OperationResult:
    if not ctx.inputs:
        raise ValidationError("Select at least one image.")

    page_size = str(ctx.options.get("pageSize", "fit")).lower()
    if page_size != "fit" and page_size not in _PAGE_SIZES:
        raise ValidationError("Page size must be fit, A4 or Letter.")
    margin_key = str(ctx.options.get("margin", "none")).lower()
    margin = _MARGINS.get(margin_key)
    if margin is None:
        raise ValidationError("Margin must be none, small or large.")

    output = ctx.workdir / "images.pdf"
    total = len(ctx.inputs)
    with fitz.open() as document:
        for index, path in enumerate(ctx.inputs):
            data, width, height, dpi = _prepare_image(path)
            page_rect, image_rect = _layout(width, height, dpi, page_size, margin)
            page = document.new_page(width=page_rect.width, height=page_rect.height)
            page.insert_image(image_rect, stream=data, keep_proportion=True)
            ctx.progress(30 + int(55 * (index + 1) / total), "converting")
        document.save(output, garbage=3, deflate=True)

    name = (
        f"{_stem(ctx.original_names[0])}.pdf" if total == 1 else "images.pdf"
    )
    return OperationResult(
        output,
        name,
        {"pageCount": total, "pageSize": page_size, "margin": margin_key},
    )


# --- PDF -> images -----------------------------------------------------

_FORMATS = {"png": "png", "jpeg": "jpg", "webp": "webp"}
_DPIS = (72, 150, 300)
# One rendered page is held in memory at a time. 40 megapixels is A3 at 300
# DPI with room to spare; an oversized page is rendered at a lower DPI rather
# than refused, so a single poster page does not fail a whole document.
MAX_RENDER_PIXELS = 40_000_000
_IMAGE_QUALITY = 90


def _encode(pixmap: fitz.Pixmap, image_format: str) -> bytes:
    if image_format == "png":
        return pixmap.tobytes("png")
    if image_format == "jpeg":
        return pixmap.tobytes("jpeg", jpg_quality=_IMAGE_QUALITY)
    # MuPDF has no WEBP encoder, so hand the raw RGB samples to Pillow.
    image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
    buffer = io.BytesIO()
    image.save(buffer, format="WEBP", quality=_IMAGE_QUALITY, method=4)
    return buffer.getvalue()


@register("pdf_to_images")
def pdf_to_images(ctx: OperationContext) -> OperationResult:
    image_format = str(ctx.options.get("format", "png")).lower()
    extension = _FORMATS.get(image_format)
    if extension is None:
        raise ValidationError("Image format must be PNG, JPEG or WEBP.")
    dpi = ctx.options.get("dpi", 150)
    if type(dpi) is not int or dpi not in _DPIS:
        raise ValidationError("Resolution must be 72, 150 or 300 DPI.")

    stem = _stem(ctx.original_names[0])
    output = ctx.workdir / "images.zip"
    downscaled = 0

    try:
        document = fitz.open(ctx.inputs[0])
    except (fitz.FileDataError, RuntimeError) as exc:
        raise ValidationError("This file is not a readable PDF.") from exc

    with document:
        if document.is_encrypted:
            raise ValidationError("This PDF is password protected. Unlock it first.")
        page_count = document.page_count
        if page_count == 0:
            raise ValidationError("This PDF has no pages.")
        indices = parse_pages(ctx.options.get("pages"), page_count)
        digits = len(str(page_count))

        # PNG, JPEG and WEBP are already compressed; deflating them again only
        # burns CPU, so entries are stored as-is.
        with zipfile.ZipFile(output, "w", zipfile.ZIP_STORED) as archive:
            for position, index in enumerate(indices, start=1):
                page = document[index]
                zoom = dpi / 72.0
                pixels = page.rect.width * zoom * page.rect.height * zoom
                if pixels > MAX_RENDER_PIXELS:
                    # MuPDF rounds pixel dimensions up, so leave a little slack.
                    zoom *= math.sqrt(MAX_RENDER_PIXELS / pixels) * 0.99
                    downscaled += 1
                pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
                archive.writestr(
                    f"{stem}-page-{index + 1:0{digits}d}.{extension}",
                    _encode(pixmap, image_format),
                )
                del pixmap
                ctx.progress(30 + int(60 * position / len(indices)), "rendering")

    return OperationResult(
        output,
        f"{stem}-images.zip",
        {
            "imageCount": len(indices),
            "format": image_format,
            "dpi": dpi,
            "downscaledPages": downscaled,
        },
    )
