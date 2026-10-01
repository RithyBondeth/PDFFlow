"""Extract Images: pull the images embedded in a PDF out into a ZIP.

Images are found per page but extracted per object: a logo repeated on every
page is one image object in the file, so it is written once. JPEGs are
copied out byte for byte by default, since re-encoding would only lose
quality. Everything else becomes PNG, including images whose transparency is
stored as a separate soft mask, which is recombined so the alpha survives.

Inline images (drawn directly in a page's content stream rather than stored
as objects) are not reachable this way and are not extracted.
"""

from __future__ import annotations

import zipfile

import fitz  # PyMuPDF

from app.core.errors import ValidationError
from app.worker.operations import OperationContext, OperationResult, register
from app.worker.operations.pageranges import parse as parse_pages
from app.worker.operations.pdf_ops import _stem

# Below this on either side an image is almost always a rule, a bullet or a
# spacer rather than something a person wants back.
SMALL_IMAGE_PX = 32
MAX_IMAGES = 2000
# Decoding is only needed for conversion; this bounds the memory it can take.
MAX_DECODE_PIXELS = 100_000_000


def _png(doc: fitz.Document, xref: int, smask: int) -> bytes:
    """Decode an image object and encode it as PNG, keeping any soft mask."""
    pixmap = fitz.Pixmap(doc, xref)
    # CMYK and other colour spaces PNG cannot hold are converted to RGB.
    if pixmap.colorspace and pixmap.colorspace.n not in (1, 3):
        pixmap = fitz.Pixmap(fitz.csRGB, pixmap)
    if smask:
        mask = fitz.Pixmap(doc, smask)
        if pixmap.alpha:
            pixmap = fitz.Pixmap(pixmap, 0)
        pixmap = fitz.Pixmap(pixmap, mask)
    return pixmap.tobytes("png")


@register("extract_images")
def extract_images(ctx: OperationContext) -> OperationResult:
    image_format = ctx.options.get("format", "original")
    if image_format not in ("original", "png"):
        raise ValidationError("Image format must be original or png.")
    skip_small = ctx.options.get("skipSmall", True)
    if not isinstance(skip_small, bool):
        raise ValidationError("skipSmall must be true or false.")

    try:
        document = fitz.open(ctx.inputs[0])
    except (fitz.FileDataError, RuntimeError) as exc:
        raise ValidationError("This file is not a readable PDF.") from exc

    stem = _stem(ctx.original_names[0])
    output = ctx.workdir / "images.zip"
    seen: set[int] = set()
    written = skipped_small = skipped_large = 0

    with document:
        if document.is_encrypted:
            raise ValidationError("This PDF is password protected. Unlock it first.")
        indices = parse_pages(ctx.options.get("pages"), document.page_count)
        digits = len(str(document.page_count))

        # Encoded images are already compressed; deflating them again is waste.
        with zipfile.ZipFile(output, "w", zipfile.ZIP_STORED) as archive:
            for position, index in enumerate(indices, start=1):
                number_on_page = 0
                for image in document[index].get_images(full=True):
                    xref, smask, width, height = image[0], image[1], image[2], image[3]
                    if xref in seen:
                        continue
                    seen.add(xref)

                    if skip_small and min(width, height) < SMALL_IMAGE_PX:
                        skipped_small += 1
                        continue
                    if width * height > MAX_DECODE_PIXELS:
                        skipped_large += 1
                        continue
                    if written >= MAX_IMAGES:
                        raise ValidationError(
                            f"This PDF has more than {MAX_IMAGES} images. "
                            "Choose fewer pages and try again."
                        )

                    try:
                        info = document.extract_image(xref)
                        if (
                            image_format == "original"
                            and info.get("ext") in ("jpeg", "jpg")
                            and not smask
                        ):
                            data, extension = info["image"], "jpg"
                        else:
                            data, extension = _png(document, xref, smask), "png"
                    except (RuntimeError, ValueError):
                        # One damaged image should not cost the user the rest.
                        continue

                    number_on_page += 1
                    written += 1
                    page_label = f"{index + 1:0{digits}d}"
                    archive.writestr(
                        f"{stem}-page-{page_label}-{number_on_page}.{extension}", data
                    )
                ctx.progress(30 + int(60 * position / len(indices)), "extracting")

    if written == 0:
        output.unlink(missing_ok=True)
        if skipped_small:
            raise ValidationError(
                "This PDF only has very small images (icons or lines). "
                "Turn off “Skip tiny images” to include them."
            )
        raise ValidationError("No embedded images were found in these pages.")

    return OperationResult(
        output,
        f"{stem}-images.zip",
        {
            "imageCount": written,
            "skippedSmall": skipped_small,
            "skippedLarge": skipped_large,
        },
    )
