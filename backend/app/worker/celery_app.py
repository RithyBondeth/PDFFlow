from __future__ import annotations

from celery import Celery
from celery.signals import setup_logging as celery_setup_logging

from app.core.config import settings
from app.core.logging import configure_logging

celery_app = Celery(
    "pdfflow",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_default_queue="pdf",
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # PDF work is CPU-bound: take one task at a time so a large document does
    # not sit behind a prefetched queue on a busy worker.
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=600,
    task_soft_time_limit=540,
    result_expires=3600,
    beat_schedule={
        "cleanup-expired": {
            "task": "pdfflow.cleanup_expired",
            "schedule": float(settings.cleanup_interval_seconds),
            "options": {"queue": "maintenance", "expires": 240},
        }
    },
)


@celery_setup_logging.connect
def _configure(**_: object) -> None:
    configure_logging()
