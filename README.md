# PDFFlow

**Fast, Private PDF Tools. No Signup Required.**

PDFFlow is a privacy-first PDF processing platform. You upload a document, pick
a tool, download the result, and leave. There is no account, no session cookie,
no analytics, and no permanent storage — uploaded files live in a temporary
directory under a generated name and are deleted automatically.

---

## Contents

- [Why it is built this way](#why-it-is-built-this-way)
- [Architecture](#architecture)
- [File lifecycle](#file-lifecycle)
- [Features](#features)
- [Technology stack](#technology-stack)
- [Getting started](#getting-started)
- [Environment variables](#environment-variables)
- [API](#api)
- [Project structure](#project-structure)
- [Testing](#testing)
- [Deployment](#deployment)
- [Roadmap](#roadmap)

---

## Why it is built this way

Three product constraints drove nearly every technical decision:

**No accounts.** There is no user table, no auth middleware and no session. The
only identifier in the system is a job UUID that the browser holds in memory.
This removes an entire class of security surface — but it also means rate
limiting has to key on IP, and a page reload genuinely loses your work, because
there is nowhere to restore it from.

**No permanent storage.** Files are written to a `tmpfs` volume, so in the
default Docker setup user documents never touch durable disk at all. The
database stores *metadata about* files — never their contents.

**Deletion is enforced, not promised.** Inputs are removed the moment a job
reaches a terminal state. A Celery beat sweep runs every five minutes and
deletes anything past its TTL, plus any orphaned file on disk with no database
row at all.

## Architecture

```
                        ┌──────────────┐
                        │ User Browser │
                        └──────┬───────┘
                               │ HTTPS
                        ┌──────▼───────┐
                        │    Nginx     │  rate limits, SSE pass-through
                        └──┬────────┬──┘
                  static   │        │  /api
                  ┌────────▼──┐  ┌──▼────────┐
                  │  Nuxt 4   │  │  FastAPI  │
                  └───────────┘  └──┬─────┬──┘
                                    │     │
                        ┌───────────▼─┐ ┌─▼──────────┐
                        │ PostgreSQL  │ │   Redis    │
                        │ job metadata│ │ queue+pubsub│
                        └─────────────┘ └─┬──────────┘
                                          │
                                   ┌──────▼───────┐
                                   │Celery Worker │
                                   └──────┬───────┘
                                          │
                                ┌─────────▼──────────┐
                                │ Temporary storage  │
                                │  (tmpfs volume)    │
                                └────────────────────┘
```

Redis does double duty: it is the Celery broker *and* the pub/sub bus that
carries progress events from the worker back to whichever API process is
holding the browser's SSE connection. That indirection is what lets the API
scale horizontally without a client losing its progress stream.

## File lifecycle

| Step | What happens | Where |
| --- | --- | --- |
| 1. Upload | Content sniffed, size-capped, written as `<uuid>.<ext>` | `storage/uploads/` |
| 2. Job created | Row in `jobs`, task pushed to Redis | PostgreSQL + Redis |
| 3. Processing | Worker emits `job_progress` at 10/30/70/100 | Celery |
| 4. Result | Written as a new UUID under `processed/` | `storage/processed/` |
| 5. Inputs purged | Deleted immediately when the job ends | worker `finally:` block |
| 6. Expiry | Result deleted, job marked `expired` | beat sweep, every 5 min |

Default TTL is **30 minutes** (`FILE_TTL_MINUTES`).

## Features

Working end to end today:

- **Merge PDF** — combine several documents, order set by drag and drop
- **Split PDF** — one PDF per page, or by explicit page ranges → ZIP
- **Extract Pages** — build a new document from a page selection
- **Rotate PDF** — 90/180/270°, whole document or selected pages
- **Compress PDF** — low/medium/high, reports original vs. compressed size

Catalogued and surfaced in the UI as *Soon*, with handlers still to be written
(see [Roadmap](#roadmap)): Organize Pages, Watermark, Protect, Unlock, Extract
Images, Images→PDF, PDF→Images, Office→PDF.

The tool catalog lives in one place ([`backend/app/services/operations.py`](backend/app/services/operations.py))
and is served to the frontend over `/api/operations`, so the picker can never
advertise a tool the worker cannot run.

## Technology stack

| Layer | Choice |
| --- | --- |
| Frontend | Nuxt 4, Vue 3 (Composition API), TypeScript, Tailwind CSS v4, Nuxt UI, Pinia, VueUse |
| API | FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic |
| Worker | Celery 5, PyMuPDF, pypdf, Pillow, LibreOffice (headless) |
| Data | PostgreSQL 16, Redis 7 |
| Infra | Docker Compose, Nginx |

## Getting started

### With Docker (recommended)

```bash
cp .env.example .env
docker compose up --build
```

Then open <http://localhost:8080>. API docs are at
<http://localhost:8080/docs>.

Migrations run automatically: the `migrate` service applies `alembic upgrade
head` before the API and worker are allowed to start.

### Local development

Backend:

```bash
cd backend && python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
```

```bash
cd backend && .venv/bin/uvicorn app.main:app --reload
```

Worker (needs Redis and Postgres running):

```bash
cd backend && .venv/bin/celery -A app.worker.celery_app.celery_app worker --loglevel=info
```

Beat scheduler, for the cleanup sweep:

```bash
cd backend && .venv/bin/celery -A app.worker.celery_app.celery_app beat --loglevel=info
```

Frontend:

```bash
cd frontend && npm install && npm run dev
```

## Environment variables

Every value has a working default; see [`.env.example`](.env.example).

| Variable | Default | Purpose |
| --- | --- | --- |
| `HTTP_PORT` | `8080` | Host port Nginx binds to |
| `DATABASE_URL` | local Postgres | SQLAlchemy URL (psycopg 3) |
| `REDIS_URL` | `redis://redis:6379/0` | Broker, result backend and event bus |
| `STORAGE_ROOT` | `/data/storage` | Parent of `uploads/` and `processed/` |
| `MAX_UPLOAD_BYTES` | `104857600` | Per-file ceiling, enforced while streaming |
| `MAX_FILES_PER_JOB` | `25` | Upper bound on a single job |
| `FILE_TTL_MINUTES` | `30` | How long anything survives |
| `CLEANUP_INTERVAL_SECONDS` | `300` | Beat sweep cadence |
| `CORS_ORIGINS` | localhost | Comma-separated allow-list |
| `RATE_LIMIT_UPLOADS` | `30/minute` | Per-IP upload budget |
| `RATE_LIMIT_JOBS` | `60/minute` | Per-IP job-creation budget |
| `TRUSTED_PROXIES` | loopback + private ranges | Networks whose `X-Forwarded-For` is believed |

## API

Interactive Swagger UI at `/docs`, ReDoc at `/redoc`, schema at
`/openapi.json`.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Liveness plus Postgres and Redis reachability |
| `GET` | `/api/config` | Client-visible limits |
| `GET` | `/api/operations` | The tool catalog |
| `POST` | `/api/upload` | Multipart upload → file ids + applicable tools |
| `POST` | `/api/jobs/create` | Queue an operation over uploaded file ids |
| `GET` | `/api/jobs/{id}` | Full job record |
| `GET` | `/api/jobs/{id}/status` | Lightweight status, for polling |
| `GET` | `/api/jobs/{id}/events` | SSE stream: `job_created`, `job_progress`, `job_completed`, `job_failed` |
| `GET` | `/api/download/{id}` | Result download |

Errors are uniform and deliberately sparse — no paths, no stack traces, no
stored filenames:

```json
{ "error": { "code": "file_too_large", "message": "File exceeds the 100 MB limit.", "requestId": "a1b2c3d4e5f6" } }
```

The `requestId` also comes back as an `X-Request-Id` header and is what appears
in the server logs, so a user report can be traced without exposing internals.

## Project structure

```
pdfflow/
├── frontend/                 Nuxt 4 application
│   └── app/
│       ├── components/       DropZone, FileList, ToolCard, JobStatus, …
│       ├── composables/      useApi, useJobStream
│       ├── pages/            index (landing), workspace
│       └── stores/           workspace (Pinia)
├── backend/
│   ├── app/
│   │   ├── api/routes/       health, upload, jobs, download
│   │   ├── core/             config, errors, logging
│   │   ├── db/               engine, session, declarative base
│   │   ├── models/           Job, FileRecord
│   │   ├── schemas/          Pydantic request/response models
│   │   ├── services/         storage, validation, jobs, events, rate limiting
│   │   └── worker/           Celery app, tasks, operations/
│   └── tests/
├── database/migrations/      Alembic
├── infrastructure/           docker-compose.yml, nginx/
└── docs/                     architecture, security
```

## Testing

```bash
cd backend && .venv/bin/pytest
```

61 tests, no external services needed — the API suite runs against SQLite with
Celery dispatch called inline, so it exercises the real upload → job → download
path. Coverage focuses on the things that would hurt: path-traversal defences,
the streaming size ceiling, MIME/extension mismatch detection, page-range
parsing, every implemented PDF operation against a real generated PDF, error
messages that must not leak internals, and the cleanup sweep.

Frontend tests run with Vitest:

```bash
cd frontend && npm test
```

These cover the formatting utilities and the workspace store. Component
rendering is *not* under test: `@nuxt/test-utils`' Nuxt environment does not
currently boot under Vitest 3, and rather than pin an older toolchain the
components are left to `vue-tsc` and the production build. Restoring
`mountSuspended` coverage is worth doing once that combination works.

## Deployment

The Compose file is production-shaped but not production-configured. Before
exposing it:

1. **Terminate TLS.** Put a certificate on the Nginx service (or run it behind
   a load balancer) and redirect port 80.
2. **Change `POSTGRES_PASSWORD`** and set `ENVIRONMENT=production`,
   `DEBUG=false`.
3. **Set `CORS_ORIGINS`** to your real origin only, and **`TRUSTED_PROXIES`**
   to the network your load balancer actually sits in. Leaving it wider than
   necessary means anything inside that range can forge a client IP and slip
   the rate limits.
4. **Keep exactly one `beat` replica.** Scale `worker` and `api` freely; a
   second beat would double every cleanup sweep.
5. **Size the tmpfs volume** for your traffic — it is RAM. The default 2 GB
   holds roughly 20 concurrent maximum-size jobs.
6. **Watch `/api/health`**, which reports Postgres and Redis separately and
   returns 503 when either is down.

## Roadmap

The architecture leaves room for the obvious next steps without a rewrite:

- **Remaining tools.** Each is one function registered with `@register(key)` in
  `app/worker/operations/` — the dispatcher, progress reporting and cleanup are
  already generic.
- **User accounts.** `Job` and `FileRecord` would take a nullable `owner_id`;
  anonymous jobs keep working exactly as they do now.
- **Premium plans.** Limits already flow from settings, so they can become
  per-request values rather than globals.
- **Durable storage.** `services/storage.py` is the only module that touches the
  filesystem, and it is written against a small bucket API.
- **API access / extension / desktop app.** The REST surface is already the
  whole product; the frontend is just its first client.
