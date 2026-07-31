"""Importing this package registers every model with ``Base.metadata``."""

from app.db.base import Base
from app.models.file_record import FileRecord
from app.models.job import Job, JobStatus

__all__ = ["Base", "FileRecord", "Job", "JobStatus"]
