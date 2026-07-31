"""Cleanup sweep tests — the mechanism the privacy promise rests on."""

import io
from datetime import timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.time import now as utc_now
from app.models import Base, FileRecord, Job, JobStatus
from app.services import storage


@pytest.fixture
def db_factory(monkeypatch: pytest.MonkeyPatch, isolated_storage):
    from app.db import session as db_session
    from app.services import events

    monkeypatch.setattr(events, "publish", lambda *a, **k: None)

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(db_session, "SessionLocal", factory)
    return factory


def make_upload(content: bytes = b"%PDF-1.7 data") -> str:
    name, _ = storage.save_stream(io.BytesIO(content), extension=".pdf")
    return name


def test_expired_upload_is_deleted_and_marked(db_factory):
    from app.worker.tasks import cleanup_expired

    stored = make_upload()
    with db_factory() as db:
        db.add(
            FileRecord(
                original_name="old.pdf",
                stored_name=stored,
                size=10,
                mime_type="application/pdf",
                expires_at=utc_now() - timedelta(minutes=1),
            )
        )
        db.commit()

    result = cleanup_expired()

    assert result["filesRemoved"] == 1
    assert not (storage.settings.upload_dir / stored).exists()
    with db_factory() as db:
        assert db.query(FileRecord).one().deleted is True


def test_unexpired_upload_survives(db_factory):
    from app.worker.tasks import cleanup_expired

    stored = make_upload()
    with db_factory() as db:
        db.add(
            FileRecord(
                original_name="fresh.pdf",
                stored_name=stored,
                size=10,
                mime_type="application/pdf",
                expires_at=utc_now() + timedelta(minutes=30),
            )
        )
        db.commit()

    cleanup_expired()

    assert (storage.settings.upload_dir / stored).exists()


def test_expired_job_result_is_deleted_and_job_marked_expired(db_factory):
    from app.worker.tasks import cleanup_expired

    name, _ = storage.save_stream(
        io.BytesIO(b"result"), extension=".pdf", bucket="processed"
    )
    with db_factory() as db:
        db.add(
            Job(
                operation="compress",
                status=JobStatus.completed,
                progress=100,
                output_stored_name=name,
                output_filename="out.pdf",
                expires_at=utc_now() - timedelta(seconds=1),
            )
        )
        db.commit()

    result = cleanup_expired()

    assert result["jobsExpired"] == 1
    assert not (storage.settings.processed_dir / name).exists()
    with db_factory() as db:
        job = db.query(Job).one()
        assert job.status == JobStatus.expired
        # The reference is cleared too, so nothing can point at a deleted file.
        assert job.output_stored_name is None


def test_orphan_on_disk_is_swept_even_without_a_row(db_factory):
    """A crash mid-upload can leave a file with no database row at all."""
    import os
    import time

    from app.worker.tasks import cleanup_expired

    stored = make_upload()
    path = storage.settings.upload_dir / stored
    ancient = time.time() - 60 * 60 * 24
    os.utime(path, (ancient, ancient))

    result = cleanup_expired()

    assert result["orphansRemoved"] == 1
    assert not path.exists()


def test_sweep_is_idempotent(db_factory):
    from app.worker.tasks import cleanup_expired

    assert cleanup_expired() == {
        "filesRemoved": 0,
        "jobsExpired": 0,
        "orphansRemoved": 0,
    }
