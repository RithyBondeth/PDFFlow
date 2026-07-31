# Shared image for the API and the Celery worker — same code, different command.
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- api ---------------------------------------------------------------
FROM base AS api
COPY backend /app
COPY database /database
RUN useradd --create-home --uid 10001 pdfflow \
    && mkdir -p /data/storage/uploads /data/storage/processed \
    && chown -R pdfflow:pdfflow /data/storage
USER pdfflow
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# --- worker ------------------------------------------------------------
# NOTE: the office_to_pdf operation needs LibreOffice headless. It is not
# implemented yet, and installing three LibreOffice suites adds ~1 GB and
# ~25 minutes to every worker build, so the dependency lands with the feature.
# When implementing it, uncomment:
#
#   RUN apt-get update && apt-get install -y --no-install-recommends \
#           libreoffice-writer libreoffice-calc libreoffice-impress \
#           fonts-dejavu-core \
#       && rm -rf /var/lib/apt/lists/*
FROM base AS worker
COPY backend /app
COPY database /database
RUN useradd --create-home --uid 10001 pdfflow \
    && mkdir -p /data/storage/uploads /data/storage/processed \
    && chown -R pdfflow:pdfflow /data/storage
USER pdfflow
CMD ["celery", "-A", "app.worker.celery_app.celery_app", "worker", \
     "--loglevel=info", "--queues=pdf,maintenance", "--concurrency=2"]
