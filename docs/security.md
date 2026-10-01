# PDFFlow — Security notes

A short, honest account of what is defended, how, and what is deliberately not
defended. See [architecture.md](architecture.md) for the surrounding design.

## Threat model

PDFFlow accepts arbitrary binary files from anonymous users on the public
internet, runs third-party parsing libraries over them, and hands back a
result. The realistic threats are:

1. A malicious *filename* used to write or read outside the storage directory.
2. A malicious *file* that exploits a parser, or that is simply enormous.
3. Volumetric abuse — using a free service as compute or as storage.
4. Information disclosure through error messages.
5. One user obtaining another user's document.

## 1. Filenames are never trusted

The uploaded name is used for exactly two things: display in the UI, and the
`Content-Disposition` on download. It never reaches the filesystem.

- On-disk names are `<uuid4-hex>.<ext>`, with the extension taken from a fixed
  allow-list (`services/validation.py`).
- `storage.resolve()` rejects any name containing a separator, `.`, or `..`,
  then resolves the path and asserts it is inside the bucket directory. Both
  paths are resolved first, so a symlink cannot be used to escape either.
- `safe_display_name()` strips directory components and non-printable
  characters and truncates to 200 characters before a name is echoed back.

Covered by `tests/test_storage.py` and `tests/test_validation.py`.

## 2. File content is validated, and bounded

- **Magic bytes decide the type.** The declared `Content-Type` and the
  extension are hints; `sniff()` reads the header and a mismatch is a 415. A
  PNG renamed `.pdf` is rejected.
- **Images are bounded by pixels, not just bytes.** A small PNG can declare
  tens of thousands of pixels a side and inflate to gigabytes when decoded.
  `validate_image()` reads the dimensions from the header — without decoding
  pixel data — and rejects anything over 100 megapixels, then verifies the
  file structure and that the real format matches the extension (a PNG
  renamed `.jpg` shares the image family, so only this step catches it).
  Rendering PDF pages is bounded too: a page that would exceed 40 megapixels
  at the requested DPI is rendered at a lower resolution instead.
- **Size is enforced while streaming.** `save_stream` counts bytes as it
  writes and aborts past the ceiling, deleting the partial file. A lying
  `Content-Length` achieves nothing. Nginx has its own `client_max_body_size`
  as a first line.
- **Time is bounded.** Celery soft/hard limits (540s/600s) stop a pathological
  document from occupying a worker indefinitely; the soft limit is caught and
  turned into a user-facing message.
- **Parsers run in the worker, not the API.** A crash takes down a task, not
  the web tier. Workers run as an unprivileged user (uid 10001).
- **No shell.** No implemented operation passes user input to a command line.
  When LibreOffice conversion is added it must be invoked with an argument
  list — never a shell string, and never with a user-supplied filename.

## 3. Abuse

Two layers, because the application layer can be bypassed if the app is ever
exposed directly:

- Nginx: `limit_req` zones, 30 r/m for uploads and 300 r/m general, per IP.
- Application: slowapi with counters in Redis, so replicas share one budget.

Which IP the application layer keys on is the whole game, and it is easy to
get backwards. Nginx forwards with `$proxy_add_x_forwarded_for`, which
*appends* the real peer to any `X-Forwarded-For` the caller already sent. A
request carrying `X-Forwarded-For: 1.2.3.4` therefore arrives as
`1.2.3.4, <real peer>` — so **reading the left of that list keys the limiter
on a caller-chosen value**, and rotating it per request slips every limit.
This is precisely the bug that shipped in Phase 1.

The rule now is:

- Forwarding headers are consulted **only** when the connection itself came
  from a network in `TRUSTED_PROXIES`. Pointed straight at the API, the peer
  address is used and headers are ignored — so bypassing nginx cannot be used
  to forge an identity.
- From a trusted peer, the client is the **rightmost** entry that is not
  itself a trusted proxy. That is correct for a chain (load balancer → nginx →
  api) as long as each hop is listed, and it cannot be shifted by padding the
  header with forged hops, including ones that look private.

Covered by `tests/test_rate_limit_key.py` and
`tests/test_api.py::test_rotating_forwarded_for_cannot_slip_the_upload_limit`,
which drives 31 uploads through the real stack with a different forged origin
each time and asserts the 31st is still refused.

Storage abuse is bounded by the TTL: nothing survives 30 minutes, and the
default storage volume is a 2 GB tmpfs, so the worst case is bounded by RAM
rather than by disk filling silently.

**Caveat:** IP-based limiting is the only option without accounts. It is
weak against distributed abuse and unfair behind large NATs. If abuse becomes
a real problem, a proof-of-work challenge on upload is the option that
preserves the no-signup property.

## 4. Errors say nothing useful to an attacker

Every response body is `{"error": {"code", "message", "requestId"}}`.

- Only `PDFFlowError` subclasses carry a message chosen for a user.
- Every other exception is caught by the handler in `main.py`, logged with its
  traceback, and returned as a generic 500 with a request id.
- Job failures follow the same rule: `mark_failed` is only ever called with a
  vetted string, never `str(exc)`.
- `server_tokens off` in Nginx; `X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy` and `Permissions-Policy` are set on every response.

`tests/test_api.py::test_failed_job_reports_a_safe_message` asserts this.

## 5. Access control — the deliberate gap

There is none, because there are no accounts. **A download URL is a bearer
capability:** anyone holding the job UUID can fetch that result until it
expires.

What makes this acceptable:

- The identifier is a version-4 UUID (122 bits of entropy) — not enumerable.
- The window is 30 minutes, after which the file is gone.
- Results are never listed, indexed, or linked from anywhere.
- `Cache-Control: no-store` on downloads keeps results out of shared caches.

What would break it: logging full URLs to an aggregator, putting a job id in a
`Referer`-leaking link, or lengthening the TTL substantially. Treat job ids as
secrets.

## 6. Document passwords are used once and never kept

Protect and Unlock need the user's password, which is more sensitive than any
other option. It is handled differently from everything else:

- **Never in Postgres.** `jobs.create_job` splits `password` off the options
  before the job row is written (`services/job_secrets.py`), so `jobs.options`
  only ever holds the non-secret choices, such as `allowPrinting`.
- **Never in the Celery message.** The task carries the job id only.
- **Handed over once.** The API stores the password in Redis under the job id
  with a TTL equal to the file TTL. The worker reads it with `GETDEL` as its
  first action, which deletes it in the same step, before any early return.
  If no worker ever runs the job, the TTL deletes it.
- **Never echoed.** Validation errors use the generic envelope, failure
  messages are fixed strings ("That password is not correct."), and result
  metadata holds no password. Tests assert it is absent from the database,
  Redis, responses and captured logs after a job.
- **Cleared in the browser.** The workspace drops the password from memory
  as soon as the job is created. The confirmation field is never sent.

Permissions (no printing, no copying) are written with a random owner
password that nobody is told. Otherwise the user password would also be the
owner password, which grants every permission and voids the restriction. The
UI says plainly that PDF permissions are honoured by most readers but are not
a guarantee.

Encrypted uploads are accepted and flagged (`file_records.encrypted`). The
flag keeps them away from every tool except Unlock, and keeps Unlock away
from PDFs that are not protected. Repeated guessing costs a fresh upload and
job per attempt, both rate limited.

**Redis must not persist to disk.** The bundled Compose Redis runs with
`--save "" --appendonly no`, so a password exists only in memory, for at most
the TTL. A managed Redis that snapshots to disk could write one there; disable
persistence on it, or accept that risk explicitly.

## Deployment checklist

- [ ] Started with `docker-compose.prod.yml` **and** `--env-file .env`. Without
      the flag Compose reads no `.env` at all and silently uses the
      development defaults, `POSTGRES_PASSWORD` among them.
- [ ] TLS terminated; port 80 redirects; HSTS present on a real response
      (`curl -sI https://<host>/ | grep -i strict-transport`).
- [ ] `POSTGRES_PASSWORD` changed from the example value — and verified inside
      the container, not just in the file.
- [ ] `CORS_ORIGINS` set to the real origin only — not a wildcard.
- [ ] `DEBUG=false`, `ENVIRONMENT=production`.
- [ ] Storage volume is tmpfs, or on an encrypted disk if it must be durable.
- [ ] Logs shipped somewhere that is *not* retained forever. Nginx already
      redacts job ids from access logs via the `$safe_request_uri` map in
      `nginx.conf` — if you add a log format, a downstream collector, or an
      access_log directive of your own, re-check that it does not reintroduce
      `$request` or `$request_uri`.
- [ ] Redis persistence (RDB and AOF) disabled, so job passwords never reach
      disk. See section 6.
- [ ] Exactly one `beat` replica.
- [ ] `/api/health` monitored.
