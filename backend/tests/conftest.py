from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest
from pypdf import PdfWriter


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Point storage at a per-test directory so nothing touches real uploads."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "storage_root", tmp_path / "storage")
    settings.ensure_directories()
    return settings.storage_root


@pytest.fixture
def pdf_bytes() -> bytes:
    """A minimal valid 3-page PDF."""
    writer = PdfWriter()
    for _ in range(3):
        writer.add_blank_page(width=595, height=842)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


@pytest.fixture
def pdf_file(tmp_path: Path, pdf_bytes: bytes) -> Path:
    path = tmp_path / "sample.pdf"
    path.write_bytes(pdf_bytes)
    return path


@pytest.fixture
def docx_bytes() -> bytes:
    """A small, structurally valid WordprocessingML document."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-'
            'package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.'
            'openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            "</Types>",
        )
        archive.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
            'relationships"><Relationship Id="rId1" Type="http://schemas.'
            'openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="word/document.xml"/></Relationships>',
        )
        archive.writestr(
            "word/document.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/'
            '2006/main"><w:body><w:p><w:r><w:t>PDFFlow Office conversion test'
            "</w:t></w:r></w:p><w:sectPr/></w:body></w:document>",
        )
    return buffer.getvalue()
