from __future__ import annotations

import pytest

from app.core.errors import UnsupportedFileTypeError
from app.services import validation

PDF_HEADER = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3"
PNG_HEADER = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
ZIP_HEADER = b"PK\x03\x04" + b"\x00" * 20


def test_accepts_matching_pdf() -> None:
    kind = validation.classify("report.pdf", PDF_HEADER)
    assert kind.family == "pdf"
    assert kind.mime_type == "application/pdf"


def test_normalises_jpeg_extension() -> None:
    kind = validation.classify("photo.JPEG", b"\xff\xd8\xff\xe0" + b"\x00" * 16)
    assert kind.extension == ".jpg"


def test_rejects_extension_content_mismatch() -> None:
    """A PNG renamed to .pdf is the classic upload bypass."""
    with pytest.raises(UnsupportedFileTypeError):
        validation.classify("payload.pdf", PNG_HEADER)


def test_rejects_unknown_extension() -> None:
    with pytest.raises(UnsupportedFileTypeError):
        validation.classify("script.svg", PDF_HEADER)


def test_family_restriction() -> None:
    with pytest.raises(UnsupportedFileTypeError):
        validation.classify("sheet.xlsx", ZIP_HEADER, allowed={"pdf"})


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("../../etc/passwd", "passwd"),
        ("C:\\Users\\me\\report.pdf", "report.pdf"),
        ("....pdf", "pdf"),
        (None, "document"),
        ("", "document"),
    ],
)
def test_safe_display_name(raw: str | None, expected: str) -> None:
    assert validation.safe_display_name(raw) == expected


def test_safe_display_name_is_bounded() -> None:
    assert len(validation.safe_display_name("a" * 500 + ".pdf")) <= 200
