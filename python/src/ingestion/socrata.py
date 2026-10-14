"""Helper to explore Socrata datasets and build SoQL queries.

Conventions (skill chicago-data-ingestion):
- Always filter by date window; never paginate with a deep OFFSET alone.
- Deterministic pagination via ORDER BY id.
- Optional $$app_token for rate limits.
- JSON format, page_size <= 50000 (Socrata $limit max).
"""

import json
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterator
from datetime import datetime
from typing import Any

DATASET_URL_TEMPLATE = "https://data.cityofchicago.org/resource/{dataset_id}.json"
MAX_PAGE_SIZE = 50000

FetchFn = Callable[[str, dict[str, str]], list[dict[str, Any]]]


def build_params(
    where: str | None = None,
    select: str | None = None,
    order: str | None = "id",
    limit: int | None = None,
    offset: int | None = None,
    app_token: str | None = None,
) -> dict[str, str]:
    """Build SoQL query params ($where, $select, $order, $limit, $offset)."""
    if limit is not None and not (0 < limit <= MAX_PAGE_SIZE):
        raise ValueError(f"limit must be in (0, {MAX_PAGE_SIZE}], got {limit}")
    if offset is not None and offset < 0:
        raise ValueError(f"offset must be >= 0, got {offset}")
    params: dict[str, str] = {}
    if where:
        params["$where"] = where
    if select:
        params["$select"] = select
    if order:
        params["$order"] = order
    if limit is not None:
        params["$limit"] = str(limit)
    if offset is not None:
        params["$offset"] = str(offset)
    if app_token:
        params["$$app_token"] = app_token
    return params


def date_window_where(start: str, end: str) -> str:
    """SoQL date-range filter: date >= start AND date < end (half-open).

    Args in ISO format, e.g. '2026-01-01T00:00:00'.
    """
    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end)
    if start_dt >= end_dt:
        raise ValueError(f"start ({start}) must be before end ({end})")
    return f"date >= '{start}' AND date < '{end}'"


def fetch_page(
    dataset_id: str,
    params: dict[str, str],
    timeout: int = 30,
) -> list[dict[str, Any]]:
    """GET one SoQL page as JSON records."""
    url = f"{DATASET_URL_TEMPLATE.format(dataset_id=dataset_id)}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "crimen-chicago/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        records = json.loads(resp.read().decode("utf-8"))
    if not isinstance(records, list):
        raise TypeError(f"unexpected Socrata response type: {type(records).__name__}")
    return records


def month_windows(start: str, end: str) -> list[tuple[str, str]]:
    """Split [start, end) into month-aligned half-open sub-windows.

    Backfill convention (skill chicago-data-ingestion): year/month windows,
    never a deep OFFSET without a date filter. Bounds are clipped: the first
    window starts at `start`, the last one ends at `end`, and each inner
    boundary is the first day of a month at 00:00:00.

    Mirrors the "Meses de la ventana" Code node in the n8n workflow
    (n8n/workflows/sprint2-socrata-raw.json) — keep both implementations
    in sync.

    Args in ISO format, e.g. '2026-01-01T00:00:00'.
    """
    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end)
    if start_dt >= end_dt:
        raise ValueError(f"start ({start}) must be before end ({end})")
    windows: list[tuple[str, str]] = []
    cursor = start_dt
    while cursor < end_dt:
        if cursor.month == 12:
            next_month = cursor.replace(year=cursor.year + 1, month=1, day=1)
        else:
            next_month = cursor.replace(month=cursor.month + 1, day=1)
        next_month = next_month.replace(hour=0, minute=0, second=0, microsecond=0)
        month_end = min(next_month, end_dt)
        windows.append((cursor.isoformat(), month_end.isoformat()))
        cursor = month_end
    return windows


def paginate(
    dataset_id: str,
    fetch: FetchFn,
    where: str | None = None,
    page_size: int = 50000,
    max_pages: int | None = None,
) -> Iterator[list[dict[str, Any]]]:
    """Yield full pages of records with deterministic OFFSET pagination.

    Stops when a page returns fewer records than page_size. The caller owns
    the fetch function (network or a stub in tests). Never use without a
    $where date filter on big datasets (deep OFFSET degrades).
    """
    if not (0 < page_size <= MAX_PAGE_SIZE):
        raise ValueError(f"page_size must be in (0, {MAX_PAGE_SIZE}], got {page_size}")
    offset = 0
    pages = 0
    while max_pages is None or pages < max_pages:
        params = build_params(where=where, order="id", limit=page_size, offset=offset)
        page = fetch(dataset_id, params)
        yield page
        pages += 1
        if len(page) < page_size:
            return
        offset += page_size
