from __future__ import annotations

import io

import pytest

from app.core.errors import FileTooLargeError, NotFoundError, ValidationError
from app.services import storage


@pytest.mark.parametrize(
    "name",
    [
        "../../etc/passwd",
        "..",
        "sub/dir.pdf",
        "sub\\dir.pdf",
        ".hidden",
        "",
    ],
)
def test_resolve_rejects_traversal(name: str) -> None:
    with pytest.raises(ValidationError):
        storage.resolve("uploads", name)


def test_resolve_keeps_generated_names_inside_bucket() -> None:
    name = storage.new_stored_name(".pdf")
    path = storage.resolve("uploads", name)
    assert path.parent.name == "uploads"
    assert path.name == name


def test_new_stored_name_rejects_odd_extensions() -> None:
    with pytest.raises(ValidationError):
        storage.new_stored_name(".p df")
    with pytest.raises(ValidationError):
        storage.new_stored_name(".verylongext")


def test_save_stream_roundtrip() -> None:
    payload = b"%PDF-1.7 hello"
    name, size = storage.save_stream(io.BytesIO(payload), extension=".pdf")
    assert size == len(payload)
    assert storage.open_for_read("uploads", name).read_bytes() == payload


def test_save_stream_enforces_limit_and_cleans_up() -> None:
    with pytest.raises(FileTooLargeError):
        storage.save_stream(io.BytesIO(b"x" * 500), extension=".pdf", max_bytes=100)
    # The partial write must not be left behind.
    assert list(storage.settings.upload_dir.iterdir()) == []


def test_save_stream_rejects_empty_file() -> None:
    with pytest.raises(ValidationError):
        storage.save_stream(io.BytesIO(b""), extension=".pdf")


def test_open_for_read_missing() -> None:
    with pytest.raises(NotFoundError):
        storage.open_for_read("uploads", "deadbeef.pdf")


def test_delete_is_idempotent() -> None:
    name, _ = storage.save_stream(io.BytesIO(b"data"), extension=".pdf")
    assert storage.delete("uploads", name) is True
    assert storage.delete("uploads", name) is True  # already gone: still fine
