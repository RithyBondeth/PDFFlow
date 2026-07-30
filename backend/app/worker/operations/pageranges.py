"""Parsing for the page-selection syntax used across the tools: ``1-3,5,8-10``.

Input is 1-based and inclusive because that is what users see in a PDF reader.
Output is 0-based indices, deduplicated, in ascending order.
"""

from __future__ import annotations

from app.core.errors import ValidationError

MAX_TOKENS = 200


def parse(expression: str | None, page_count: int) -> list[int]:
    """Return 0-based page indices. An empty expression means "every page"."""
    if expression is None or not expression.strip():
        return list(range(page_count))

    tokens = [token.strip() for token in expression.split(",") if token.strip()]
    if not tokens:
        return list(range(page_count))
    if len(tokens) > MAX_TOKENS:
        raise ValidationError("Too many page ranges.")

    selected: set[int] = set()
    for token in tokens:
        if "-" in token:
            raw_start, _, raw_end = token.partition("-")
            start = _to_int(raw_start, page_count)
            end = _to_int(raw_end, page_count)
            if start > end:
                start, end = end, start
            selected.update(range(start - 1, end))
        else:
            selected.add(_to_int(token, page_count) - 1)

    if not selected:
        raise ValidationError("No pages were selected.")
    return sorted(selected)


def _to_int(raw: str, page_count: int) -> int:
    value = raw.strip()
    if not value.isdigit():
        raise ValidationError(f"'{raw.strip()[:12]}' is not a valid page number.")
    number = int(value)
    if not 1 <= number <= page_count:
        raise ValidationError(
            f"Page {number} is out of range — this document has {page_count} pages."
        )
    return number
