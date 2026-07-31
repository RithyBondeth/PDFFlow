from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.job import JobStatus


def _camel(name: str) -> str:
    head, *tail = name.split("_")
    return head + "".join(word.capitalize() for word in tail)


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=_camel, populate_by_name=True, from_attributes=True
    )


class FileOut(ApiModel):
    id: uuid.UUID
    original_name: str
    size: int
    mime_type: str
    family: str
    page_count: int | None = None
    expires_at: datetime


class UploadResponse(ApiModel):
    files: list[FileOut]
    available_operations: list[dict]


class JobCreate(ApiModel):
    operation: str = Field(min_length=1, max_length=64)
    file_ids: list[uuid.UUID] = Field(min_length=1, max_length=25)
    options: dict = Field(default_factory=dict)

    @field_validator("options")
    @classmethod
    def _bounded_options(cls, value: dict) -> dict:
        if len(value) > 32:
            raise ValueError("Too many options.")
        return value


class JobOut(ApiModel):
    id: uuid.UUID
    operation: str
    status: JobStatus
    progress: int
    stage: str | None = None
    error_message: str | None = None
    input_filename: str | None = None
    output_filename: str | None = None
    output_size: int | None = None
    created_at: datetime
    completed_at: datetime | None = None
    expires_at: datetime


class JobStatusOut(ApiModel):
    """Lightweight shape used by polling and by SSE frames."""

    id: uuid.UUID
    status: JobStatus
    progress: int
    stage: str | None = None
    error_message: str | None = None


class HealthOut(ApiModel):
    status: str
    version: str
    database: str
    redis: str
