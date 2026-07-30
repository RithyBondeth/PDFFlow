"""Operation handler registry.

A handler takes a :class:`OperationContext` and returns an
:class:`OperationResult`. Adding a tool means writing one function and
decorating it with ``@register("key")`` — the dispatcher, progress reporting
and cleanup are all generic.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

Progress = Callable[[int, str], None]


@dataclass
class OperationContext:
    job_id: str
    inputs: list[Path]
    original_names: list[str]
    options: dict
    progress: Progress
    workdir: Path


@dataclass
class OperationResult:
    path: Path
    filename: str
    metadata: dict = field(default_factory=dict)


Handler = Callable[[OperationContext], OperationResult]

REGISTRY: dict[str, Handler] = {}


def register(key: str) -> Callable[[Handler], Handler]:
    def decorator(handler: Handler) -> Handler:
        REGISTRY[key] = handler
        return handler

    return decorator


def get_handler(key: str) -> Handler | None:
    return REGISTRY.get(key)


from app.worker.operations import pdf_ops  # noqa: E402,F401  (populates REGISTRY)
