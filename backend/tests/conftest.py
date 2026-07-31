from __future__ import annotations

import io
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
