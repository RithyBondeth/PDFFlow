"""Watermarking: stamp text or an image over the pages of a PDF.

The mark is drawn once as a tiny PDF page of its own, then placed with
``show_pdf_page``. That reuses a single form XObject however many times it is
tiled and however many pages it lands on, so a 500-page document does not
carry 500 copies of a logo.

Pages that declare their own /Rotate are the subtle part. A watermark has to
look right as the page is *viewed*, but PyMuPDF places content in the page's
unrotated space. Each page is therefore stamped from a sheet the size of its
visible area while its rotation is briefly set to 0, with the sheet turned by
the page's rotation, and the rotation is then restored. The tests check every
rotation, with and without an offset crop box, by rendering the result.

The layout rules below are mirrored in frontend/app/utils/watermarkLayout.ts
for the live preview. Change both together.
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image, ImageOps

from app.core.errors import ValidationError
from app.worker.operations import OperationContext, OperationResult, register
from app.worker.operations.pageranges import parse as parse_pages
from app.worker.operations.pdf_ops import _stem

MAX_TEXT_LENGTH = 100
# Helvetica Bold, one of the 14 fonts every PDF reader has, so nothing is
# embedded. PyMuPDF writes Base-14 text in Latin-1, which limits the
# characters it can show; see _font_text().
FONT = "hebo"
COLORS = {
    "gray": (0.45, 0.45, 0.45),
    "red": (0.82, 0.13, 0.13),
    "blue": (0.15, 0.35, 0.85),
    "black": (0.0, 0.0, 0.0),
}
# Width of one mark as a share of the usable span (see _span), per size.
CENTER_SIZES = {"small": 0.35, "medium": 0.55, "large": 0.75}
TILE_SIZES = {"small": 0.14, "medium": 0.2, "large": 0.28}
ANGLES = (0, 45)
MAX_TILES = 400
# Logos are downscaled to this before embedding: a watermark never needs
# more, and it keeps a 40-megapixel photo from bloating every output.
MAX_IMAGE_SIDE = 2000


@dataclass(frozen=True)
class _Mark:
    doc: fitz.Document  # one page holding the mark at its natural size
    width: float
    height: float


def _span(width: float, height: float, angle: int) -> float:
    """The length a mark may run along: the width when level, the diagonal
    of the largest centred square when at 45°."""
    return width if angle == 0 else min(width, height) * math.sqrt(2)


def _rotated_box(width: float, height: float, angle: int) -> tuple[float, float]:
    rad = math.radians(angle)
    cos, sin = abs(math.cos(rad)), abs(math.sin(rad))
    return width * cos + height * sin, width * sin + height * cos


def _choice(options: dict, key: str, allowed, default):
    value = options.get(key, default)
    if value not in allowed:
        raise ValidationError(f"Unsupported watermark {key}.")
    return value


def _opacity(options: dict) -> float:
    value = options.get("opacity", 0.3)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValidationError("Opacity must be a number between 0.05 and 1.")
    if not 0.05 <= float(value) <= 1:
        raise ValidationError("Opacity must be a number between 0.05 and 1.")
    return float(value)


def _font_text(options: dict) -> str:
    text = options.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValidationError("Enter the watermark text.")
    text = " ".join(text.split())  # one line, no runs of whitespace
    if len(text) > MAX_TEXT_LENGTH:
        raise ValidationError(
            f"Keep the watermark text to {MAX_TEXT_LENGTH} characters or fewer."
        )
    try:
        text.encode("latin-1")
    except UnicodeEncodeError:
        # Rather than silently drawing "?" for scripts the standard font
        # cannot encode (Khmer, Thai, CJK and so on), say so up front.
        raise ValidationError(
            "The watermark text uses characters PDFFlow cannot draw yet. "
            "Use Latin letters, numbers and punctuation."
        ) from None
    return text


def _text_mark(
    text: str, target_width: float, page_height: float, color, opacity: float
) -> _Mark:
    font = fitz.Font(FONT)
    size = target_width / font.text_length(text, fontsize=1)
    # Very short text ("A") would otherwise become enormous.
    size = max(6.0, min(size, page_height * 0.3, 300.0))
    width = font.text_length(text, fontsize=size)
    height = size * (font.ascender - font.descender)

    doc = fitz.open()
    page = doc.new_page(width=width, height=height)
    # insert_text with a Base-14 name references the reader's own Helvetica
    # rather than embedding a copy, which TextWriter would (about 45 KB).
    page.insert_text(
        fitz.Point(0, size * font.ascender),
        text,
        fontname=FONT,
        fontsize=size,
        color=color,
        fill_opacity=opacity,
    )
    return _Mark(doc, width, height)


def _prepare_logo(path: Path, opacity: float) -> tuple[bytes, float]:
    """Upright RGBA PNG with the opacity baked into its alpha channel, and its
    aspect ratio (height / width)."""
    try:
        with Image.open(path) as source:
            source.seek(0)
            image = (ImageOps.exif_transpose(source) or source).convert("RGBA")
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise ValidationError("The watermark image could not be read.") from exc
    image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
    if opacity < 1:
        alpha = image.getchannel("A").point(lambda value: round(value * opacity))
        image.putalpha(alpha)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue(), image.height / image.width


def _image_mark(
    png: bytes, aspect: float, target_width: float, page_height: float
) -> _Mark:
    width = target_width
    height = width * aspect
    if height > page_height * 0.8:  # a tall logo should still fit the page
        height = page_height * 0.8
        width = height / aspect
    doc = fitz.open()
    page = doc.new_page(width=width, height=height)
    page.insert_image(page.rect, stream=png)
    return _Mark(doc, width, height)


def _positions(
    page_w: float, page_h: float, box_w: float, box_h: float, layout: str
) -> list[fitz.Point]:
    """Centres for each mark: the page centre, or a staggered grid."""
    if layout == "center":
        return [fitz.Point(page_w / 2, page_h / 2)]
    gap = 0.5 * min(box_w, box_h) + 18
    step_x, step_y = box_w + gap, box_h + gap

    def grid(step_x: float, step_y: float) -> tuple[int, int]:
        # Grow outwards from the centre so the grid is symmetric on the page.
        return math.ceil(page_h / 2 / step_y) + 1, math.ceil(page_w / 2 / step_x) + 1

    rows, cols = grid(step_x, step_y)
    # Keep pathological inputs (a single tiny character) bounded.
    while (2 * rows + 1) * (2 * cols + 1) > MAX_TILES:
        step_x *= 1.25
        step_y *= 1.25
        rows, cols = grid(step_x, step_y)
    points = []
    for row in range(-rows, rows + 1):
        offset = step_x / 2 if row % 2 else 0.0
        y = page_h / 2 + row * step_y
        for col in range(-cols, cols + 1):
            points.append(fitz.Point(page_w / 2 + col * step_x + offset, y))
    return points


def _stamp_sheet(
    page_w: float, page_h: float, mark: _Mark, angle: int, layout: str
) -> fitz.Document:
    """A transparent page the size of the visible page with every mark on it."""
    box_w, box_h = _rotated_box(mark.width, mark.height, angle)
    sheet = fitz.open()
    page = sheet.new_page(width=page_w, height=page_h)
    for centre in _positions(page_w, page_h, box_w, box_h, layout):
        rect = fitz.Rect(
            centre.x - box_w / 2,
            centre.y - box_h / 2,
            centre.x + box_w / 2,
            centre.y + box_h / 2,
        )
        page.show_pdf_page(rect, mark.doc, 0, rotate=angle)
    return sheet


@register("watermark")
def watermark(ctx: OperationContext) -> OperationResult:
    pdfs = [path for path in ctx.inputs if path.suffix.lower() == ".pdf"]
    images = [path for path in ctx.inputs if path.suffix.lower() != ".pdf"]
    if len(pdfs) != 1 or len(images) > 1:
        raise ValidationError("Choose one PDF, and at most one image to stamp.")
    pdf_name = next(
        name
        for path, name in zip(ctx.inputs, ctx.original_names, strict=True)
        if path == pdfs[0]
    )

    mode = _choice(ctx.options, "mode", ("text", "image"), "text")
    if mode == "image" and not images:
        raise ValidationError("Upload an image with the PDF to use it as a watermark.")
    if mode == "text" and images:
        raise ValidationError("Remove the image, or switch to an image watermark.")
    size = _choice(ctx.options, "size", tuple(CENTER_SIZES), "medium")
    layout = _choice(ctx.options, "layout", ("center", "tile"), "center")
    angle = _choice(ctx.options, "angle", ANGLES, 45)
    opacity = _opacity(ctx.options)
    if mode == "text":
        text = _font_text(ctx.options)
        color = COLORS[_choice(ctx.options, "color", tuple(COLORS), "gray")]
    else:
        logo, aspect = _prepare_logo(images[0], opacity)

    share = (CENTER_SIZES if layout == "center" else TILE_SIZES)[size]

    try:
        document = fitz.open(pdfs[0])
    except (fitz.FileDataError, RuntimeError) as exc:
        raise ValidationError("This file is not a readable PDF.") from exc

    output = ctx.workdir / "watermarked.pdf"
    with document:
        if document.is_encrypted:
            raise ValidationError("This PDF is password protected. Unlock it first.")
        targets = parse_pages(ctx.options.get("pages"), document.page_count)

        # Pages of the same visible size share one sheet, and so one XObject.
        sheets: dict[tuple[float, float], fitz.Document] = {}
        for position, index in enumerate(targets, start=1):
            page = document[index]
            rotation = page.rotation
            visible = page.rect
            key = (round(visible.width, 2), round(visible.height, 2))
            if key not in sheets:
                target = _span(visible.width, visible.height, angle) * share
                mark = (
                    _text_mark(text, target, visible.height, color, opacity)
                    if mode == "text"
                    else _image_mark(logo, aspect, target, visible.height)
                )
                sheets[key] = _stamp_sheet(
                    visible.width, visible.height, mark, angle, layout
                )

            page.set_rotation(0)
            page.show_pdf_page(page.rect, sheets[key], 0, overlay=True, rotate=rotation)
            page.set_rotation(rotation)
            ctx.progress(30 + int(60 * position / len(targets)), "stamping")

        document.save(output, garbage=3, deflate=True)

    return OperationResult(
        output,
        f"{_stem(pdf_name)}-watermarked.pdf",
        {"mode": mode, "stampedPages": len(targets)},
    )
