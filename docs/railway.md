# Deploy PDFFlow on Railway Hobby

PDFFlow runs on Railway as four services:

- **Frontend** — the public Nuxt website
- **Backend** — FastAPI, the PDF worker and the cleanup scheduler in one image
- **Postgres** — job and file metadata
- **Redis** — the work queue and live progress events

Keeping the three backend processes together is intentional. A Railway volume
can be mounted by only one service, and all three processes must see the same
uploaded and generated files.

## 1. Create the data services

Create an empty Railway project, then add **PostgreSQL** and **Redis** from the
service catalog. Keep their generated credentials; reference variables below
will wire them to the app without copying secrets.

## 2. Add the backend

Add a service from the PDFFlow GitHub repository and use these settings:

- Branch: `main`
- Root directory: `/`
- Railway config file: `/backend/railway.toml`
- Serverless: off

Add a volume to this service and mount it at `/data/storage`. Hobby volumes are
5 GB by default, so monitor usage and keep the automatic deletion worker
running.

Set these variables (replace service names in `${{...}}` if yours differ):

```dotenv
PORT=8000
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
STORAGE_ROOT=/data/storage
ENVIRONMENT=production
DEBUG=false
MAX_UPLOAD_BYTES=104857600
MAX_FILES_PER_JOB=10
FILE_TTL_MINUTES=30
CLEANUP_INTERVAL_SECONDS=300
CORS_ORIGINS=https://pdfflow.bondeth.site
RATE_LIMIT_UPLOADS=30/minute
RATE_LIMIT_JOBS=60/minute
```

Do not generate a public domain for the backend. The frontend talks to it on
Railway's private network. The image listens on Railway's injected `PORT` and
the deployment health check uses `/api/health`.

## 3. Add the frontend

Add the same GitHub repository again as a second service:

- Branch: `main`
- Root directory: `/frontend`
- Railway config file: `/frontend/railway.toml`

The Dockerfile path is repository-absolute (`/frontend/Dockerfile`) in the
checked-in Railway configuration. Do not replace it with only `Dockerfile` in
the dashboard.

Set these variables, using the exact name of your backend service:

```dotenv
NUXT_API_INTERNAL=http://${{Backend.RAILWAY_PRIVATE_DOMAIN}}:${{Backend.PORT}}/api
NUXT_PUBLIC_API_BASE=/api
NUXT_PUBLIC_SITE_URL=https://pdfflow.bondeth.site
```

Generate a Railway domain for the frontend. When it is healthy, attach the
custom domain `pdfflow.bondeth.site` and update its DNS record using the value
Railway shows.

## 4. Verify the deployment

Open these from the public frontend domain:

1. `/api/health` — should report the API, Postgres and Redis as healthy.
2. `/api-docs` — should show production URLs in the examples.
3. Upload a DOCX, XLSX or PPTX, convert it, and download the PDF.
4. Confirm the backend logs show the API, worker and beat scheduler started.

Enable Railway's **Wait for CI** option before automatic deploys so a commit is
released only after GitHub Actions passes.

## Volume trade-offs

This setup is appropriate for a single Hobby instance. Railway does not allow
replicas on a service with a volume, and volume-backed deployments have a short
period of downtime while the old deployment releases the volume. Move files to
object storage before adding backend replicas or requiring zero-downtime
deploys.
