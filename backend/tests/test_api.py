"""End-to-end API tests.

The API is exercised against a real SQLite database and a fake Redis, with the
Celery dispatch replaced by a synchronous call to the same task function the
worker runs. That keeps the test honest — it covers the real upload, job and
download code paths — without needing Postgres or a broker.
"""

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, isolated_storage):
    from app.db import session as db_session
    from app.models import Base

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(db_session, "SessionLocal", TestSession)

    # Events go to a dev/null bus: pub/sub is covered separately and a real
    # Redis is not needed to verify the HTTP contract.
    from app.services import events

    monkeypatch.setattr(events, "publish", lambda *a, **k: None)
    monkeypatch.setattr(events, "last_event", lambda *a, **k: None)

    # The limiter stays ENABLED, with counters moved from Redis to memory.
    # Disabling it here once hid a real bug: slowapi injects rate-limit headers
    # into a Response the endpoint must declare, and with the limiter off that
    # code path never ran, so every rate-limited route 500'd in production
    # while the suite stayed green.
    from limits.storage import MemoryStorage
    from limits.strategies import MovingWindowRateLimiter

    from app.services.rate_limit import limiter

    storage = MemoryStorage()
    monkeypatch.setattr(limiter, "_storage", storage, raising=False)
    monkeypatch.setattr(
        limiter, "_limiter", MovingWindowRateLimiter(storage), raising=False
    )

    from app.api.routes import jobs as jobs_route
    from app.worker import tasks

    # Run the task inline instead of shipping it to a broker.
    monkeypatch.setattr(
        jobs_route.celery_app,
        "send_task",
        lambda name, args, **kw: tasks.process_job.run(*args),
    )

    from app.main import app

    app.dependency_overrides[db_session.get_db] = lambda: TestSession()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def upload(client, name: str, content: bytes):
    return client.post("/api/upload", files={"files": (name, content, "application/pdf")})


# --- system ------------------------------------------------------------


def test_operations_catalog_is_served(client):
    response = client.get("/api/operations")
    assert response.status_code == 200
    keys = {op["key"] for op in response.json()}
    assert {"merge", "split", "compress", "rotate"} <= keys


def test_rate_limited_routes_inject_their_headers(client, pdf_bytes):
    """Proves the slowapi header-injection path runs. It needs the endpoint to
    declare a `response: Response` parameter; without one it raises, which is
    how every rate-limited route once broke in a container while this suite
    was green."""
    response = upload(client, "doc.pdf", pdf_bytes)

    assert response.status_code == 200
    assert "x-ratelimit-limit" in response.headers
    assert "x-ratelimit-remaining" in response.headers


def test_config_exposes_limits(client):
    body = client.get("/api/config").json()
    assert body["maxUploadBytes"] > 0
    assert body["fileTtlMinutes"] == 30


# --- upload ------------------------------------------------------------


def test_upload_returns_file_and_applicable_tools(client, pdf_bytes):
    response = upload(client, "My Report.pdf", pdf_bytes)
    assert response.status_code == 200

    body = response.json()
    assert body["files"][0]["originalName"] == "My Report.pdf"
    assert body["files"][0]["family"] == "pdf"
    # A single PDF cannot be merged, so merge must not be offered.
    assert "merge" not in {op["key"] for op in body["availableOperations"]}


def test_upload_rejects_content_type_mismatch(client):
    response = upload(client, "evil.pdf", b"\x89PNG\r\n\x1a\n not a pdf")
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_file_type"


def test_upload_response_never_leaks_the_stored_name(client, pdf_bytes):
    body = upload(client, "secret.pdf", pdf_bytes).json()
    assert "storedName" not in body["files"][0]
    assert "stored_name" not in str(body)


# --- job lifecycle -----------------------------------------------------


def test_job_runs_and_result_downloads(client, pdf_bytes):
    file_id = upload(client, "doc.pdf", pdf_bytes).json()["files"][0]["id"]

    created = client.post(
        "/api/jobs/create",
        json={
            "operation": "extract_pages",
            "fileIds": [file_id],
            "options": {"pages": "1,2"},
        },
    )
    assert created.status_code == 201
    job_id = created.json()["id"]

    job = client.get(f"/api/jobs/{job_id}").json()
    assert job["status"] == "completed"
    assert job["progress"] == 100

    result = client.get(f"/api/download/{job_id}")
    assert result.status_code == 200
    assert result.headers["content-type"] == "application/pdf"
    assert "attachment" in result.headers["content-disposition"]
    assert result.content.startswith(b"%PDF")


def test_inputs_are_deleted_once_the_job_finishes(client, pdf_bytes, isolated_storage):
    file_id = upload(client, "doc.pdf", pdf_bytes).json()["files"][0]["id"]
    client.post(
        "/api/jobs/create",
        json={"operation": "compress", "fileIds": [file_id], "options": {}},
    )
    assert list((isolated_storage / "uploads").iterdir()) == []


def test_failed_job_reports_a_safe_message(client, pdf_bytes):
    file_id = upload(client, "doc.pdf", pdf_bytes).json()["files"][0]["id"]
    created = client.post(
        "/api/jobs/create",
        json={
            "operation": "extract_pages",
            "fileIds": [file_id],
            "options": {"pages": "99"},
        },
    )
    job = client.get(f"/api/jobs/{created.json()['id']}").json()

    assert job["status"] == "failed"
    message = job["errorMessage"]
    assert "out of range" in message
    # No traceback, no path, no internal identifier.
    assert "/data" not in message and "Traceback" not in message


def test_a_used_file_is_gone_after_the_job_runs(client, pdf_bytes):
    """Reusing an input is impossible because it is deleted the moment the job
    ends — the second attempt sees nothing at all."""
    file_id = upload(client, "doc.pdf", pdf_bytes).json()["files"][0]["id"]
    payload = {"operation": "compress", "fileIds": [file_id], "options": {}}

    assert client.post("/api/jobs/create", json=payload).status_code == 201
    retry = client.post("/api/jobs/create", json=payload)
    assert retry.status_code == 404
    assert retry.json()["error"]["code"] == "not_found"


def test_a_file_already_claimed_by_a_pending_job_is_refused(
    client, pdf_bytes, monkeypatch
):
    from app.api.routes import jobs as jobs_route

    monkeypatch.setattr(jobs_route.celery_app, "send_task", lambda *a, **k: None)
    file_id = upload(client, "doc.pdf", pdf_bytes).json()["files"][0]["id"]
    payload = {"operation": "compress", "fileIds": [file_id], "options": {}}

    assert client.post("/api/jobs/create", json=payload).status_code == 201
    assert client.post("/api/jobs/create", json=payload).status_code == 422


def test_merge_is_refused_for_a_single_file(client, pdf_bytes):
    file_id = upload(client, "doc.pdf", pdf_bytes).json()["files"][0]["id"]
    response = client.post(
        "/api/jobs/create",
        json={"operation": "merge", "fileIds": [file_id], "options": {}},
    )
    assert response.status_code == 422
    assert "at least 2" in response.json()["error"]["message"]


def test_unimplemented_tool_is_refused(client, pdf_bytes):
    file_id = upload(client, "doc.pdf", pdf_bytes).json()["files"][0]["id"]
    response = client.post(
        "/api/jobs/create",
        json={"operation": "protect", "fileIds": [file_id], "options": {}},
    )
    assert response.status_code == 422


def test_unknown_job_is_a_clean_404(client):
    response = client.get(f"/api/jobs/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert response.headers.get("X-Request-Id")


def test_download_before_completion_conflicts(client, pdf_bytes, monkeypatch):
    from app.api.routes import jobs as jobs_route

    monkeypatch.setattr(jobs_route.celery_app, "send_task", lambda *a, **k: None)
    file_id = upload(client, "doc.pdf", pdf_bytes).json()["files"][0]["id"]
    created = client.post(
        "/api/jobs/create",
        json={"operation": "compress", "fileIds": [file_id], "options": {}},
    )
    assert client.get(f"/api/download/{created.json()['id']}").status_code == 409


# --- merge across two files -------------------------------------------


def test_merge_of_two_uploads(client, pdf_bytes):
    body = client.post(
        "/api/upload",
        files=[
            ("files", ("a.pdf", pdf_bytes, "application/pdf")),
            ("files", ("b.pdf", pdf_bytes, "application/pdf")),
        ],
    ).json()
    assert "merge" in {op["key"] for op in body["availableOperations"]}

    ids = [file["id"] for file in body["files"]]
    created = client.post(
        "/api/jobs/create", json={"operation": "merge", "fileIds": ids, "options": {}}
    )
    job = client.get(f"/api/jobs/{created.json()['id']}").json()
    assert job["status"] == "completed"
    assert job["outputFilename"] == "merged.pdf"


def _one_page_pdf(width: int) -> bytes:
    """A single-page PDF whose page width identifies it in a merged result."""
    from io import BytesIO

    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=width, height=842)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_merge_follows_the_requested_file_order(client):
    """The order the user drags files into is the order they are combined in.

    The job is created with the ids deliberately *not* in upload order, because
    that is the case that used to break: the worker reads its inputs back
    through `Job.files`, and without an explicit ordering the database returns
    them however it likes — which happens to be upload order, silently
    discarding the reordering the user did.
    """
    from io import BytesIO

    from pypdf import PdfReader

    widths = {"a.pdf": 300, "b.pdf": 400, "c.pdf": 500}
    body = client.post(
        "/api/upload",
        files=[
            ("files", (name, _one_page_pdf(width), "application/pdf"))
            for name, width in widths.items()
        ],
    ).json()

    by_name = {file["originalName"]: file["id"] for file in body["files"]}
    requested = ["c.pdf", "b.pdf", "a.pdf"]  # reverse of the upload order

    created = client.post(
        "/api/jobs/create",
        json={
            "operation": "merge",
            "fileIds": [by_name[name] for name in requested],
            "options": {},
        },
    )
    job_id = created.json()["id"]
    assert client.get(f"/api/jobs/{job_id}").json()["status"] == "completed"

    merged = PdfReader(BytesIO(client.get(f"/api/download/{job_id}").content))
    assert [round(float(page.mediabox.width)) for page in merged.pages] == [
        widths[name] for name in requested
    ]
