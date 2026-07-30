# PDFFlow — Architecture

This document records the decisions behind the system and, where a decision was
contested, why the alternative was rejected. It is meant to be read before
changing anything structural.

---

## 1. Constraints

| Constraint | Consequence |
| --- | --- |
| No user accounts | No auth layer, no sessions. Identity is a job UUID held in browser memory. Rate limiting keys on client IP. |
| No permanent storage | Files live on a `tmpfs` volume. The database stores metadata only. |
| Automatic deletion | Two independent mechanisms (immediate purge + periodic sweep), because one is a single point of failure. |
| Background processing | PDF work is CPU-bound and can take minutes; it cannot run in a request handler. |

## 2. Components

### Nginx

Terminates client connections, applies a coarse per-IP rate limit before any
Python runs, and routes `/api` to FastAPI and everything else to Nuxt.

Two settings matter and are easy to get wrong:

- `proxy_request_buffering off` on `/api/upload`, so a 100 MB upload streams
  through rather than being spooled to Nginx's disk first.
- `proxy_buffering off` on the SSE route. With buffering on, Nginx holds every
  progress frame until the response completes — the client would see nothing,
  then everything, which defeats the purpose of streaming.

### FastAPI (`backend/app`)

Stateless. Validates and stores uploads, creates job rows, enqueues Celery
tasks, streams progress, serves results. It never processes a PDF itself.

The global exception handler in `main.py` is a security control, not just
tidiness: any exception that is not a `PDFFlowError` is logged with its
traceback and replaced with a generic message plus a request id. Server paths,
stored filenames and library internals never reach a client.

### Celery worker (`backend/app/worker`)

`process_job` is a generic dispatcher: it loads the job, resolves a handler
from the registry, runs it in a throwaway temp directory, stores the result and
purges the inputs. Adding a tool means writing one function — progress
reporting, error translation and cleanup are already handled.

Configuration worth knowing:

- `worker_prefetch_multiplier = 1` — CPU-bound tasks must not queue behind a
  prefetch buffer on one worker while another sits idle.
- `task_acks_late = True` with an idempotency check (`if job.status !=
  pending: return`) — a task redelivered after a worker crash will not redo
  completed work.
- Soft and hard time limits (540s/600s), with `SoftTimeLimitExceeded` caught
  and turned into a user-facing "this took too long" message rather than a
  silently stuck job.

### PostgreSQL

Two tables. `jobs` is the unit of work and the source of truth for expiry;
`file_records` tracks what exists on disk. `ON DELETE CASCADE` from job to
files means dropping a job row can never orphan metadata.

`options` is JSONB rather than a column per tool: options are per-operation and
open-ended, and the alternative is a migration for every new tool.

### Redis

Broker, result backend, rate-limit counters, **and** the progress event bus.

The last role is the interesting one. The worker publishes to
`pdfflow:job:<id>`; the API process holding a browser's SSE connection
subscribes. If instead the worker had called back into the API, or the API had
polled Postgres, a second API replica would break progress streaming. The last
event per job is also cached with `SETEX`, so a job that finishes before the
browser subscribes still reports its result.

## 3. Data flow

```
POST /api/upload
  ├─ sniff magic bytes, compare against extension        (validation.classify)
  ├─ stream to disk as <uuid>.<ext> under a byte ceiling (storage.save_stream)
  ├─ INSERT file_records
  └─ 200 { files, availableOperations }

POST /api/jobs/create
  ├─ validate operation, arity and file families
  ├─ INSERT jobs, claim the file rows
  ├─ Celery: send_task("pdfflow.process_job")
  └─ 201 { id, status: "pending" }

worker
  ├─ 10 %  preparing     ─┐
  ├─ 30 %  preparing      │  each step publishes job_progress
  ├─ 70 %  operation      │
  ├─ 100 % completed     ─┘
  ├─ store result under processed/<uuid>.<ext>
  └─ delete every input file

GET /api/jobs/{id}/events   (SSE, replayed-then-live)
GET /api/download/{id}      (Content-Disposition, no-store)
```

## 4. Security model

| Threat | Control |
| --- | --- |
| Path traversal via filename | Uploaded names are never used on disk. `storage.resolve` rejects separators and verifies the resolved path is inside the bucket. |
| Content-type spoofing | Magic bytes are checked against the extension; a mismatch is rejected. |
| Disk exhaustion | Size is enforced *while streaming*, not from `Content-Length`; partial writes are removed on abort. |
| Denial of service | Per-IP limits at both Nginx and the app layer; hard task time limits; bounded files per job. |
| Information disclosure | Uniform error envelope; internals logged, never returned. `Cache-Control: no-store` on downloads. |
| Guessing another user's result | Download is keyed on a v4 job UUID, and results expire in 30 minutes. |
| Shell injection | No operation shells out with user input. LibreOffice (when added) must be invoked with an argument list, never a shell string. |

**Known limitation.** With no accounts, a download URL is a bearer capability:
anyone who obtains the job UUID within its TTL can fetch the result. This is a
deliberate trade for the no-signup requirement. The mitigation is entropy plus
a short lifetime — not access control.

## 5. Cleanup

Deletion is intentionally redundant:

1. **Immediate.** The worker's `finally:` block deletes every input as soon as
   the job reaches a terminal state — success or failure.
2. **Scheduled.** `cleanup_expired` runs every five minutes: it deletes expired
   uploads and results and marks jobs `expired`.
3. **Orphan sweep.** The same task also removes any file on disk older than
   twice the TTL regardless of database state, which catches files left by a
   crash mid-upload.

Exactly one `beat` replica must run. Two would double every sweep — harmless
for deletion, but wasteful and confusing in logs.

## 6. Extension points

- **A new tool**: register a handler in `app/worker/operations/`, add an entry
  to `CATALOG` with `implemented=True`. The UI picks it up from
  `/api/operations` with no frontend change.
- **User accounts**: add a nullable `owner_id` to `jobs`; anonymous jobs keep
  working unchanged. This was the reason not to key anything on IP in the data
  model.
- **Durable storage**: `services/storage.py` is the only module that touches
  the filesystem, and its bucket API (`save_stream`, `open_for_read`, `delete`)
  maps cleanly onto object storage.
- **Horizontal scale**: API and worker are both stateless and share only
  Postgres, Redis and the storage volume.
