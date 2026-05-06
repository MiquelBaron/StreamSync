"""Normalització de payloads API (dates, ids, refs estable, llistes)."""
from __future__ import annotations

import hashlib
import re
from datetime import date as date_cls
from decimal import Decimal, InvalidOperation
from typing import Any

from django.utils.dateparse import parse_date, parse_datetime


def parse_api_date(value: Any):
    if value is None or value == "":
        return None
    if isinstance(value, date_cls):
        return value
    if hasattr(value, "date") and callable(getattr(value, "date")):
        try:
            return value.date()
        except (AttributeError, TypeError):
            pass
    s = str(value).replace("Z", "+00:00")
    d = parse_date(s[:10])
    if d:
        return d
    dt = parse_datetime(s)
    return dt.date() if dt else None


def parse_api_datetime(value: Any):
    if value is None or value == "":
        return None
    if hasattr(value, "year") and not isinstance(value, str):
        return value
    s = str(value).replace("Z", "+00:00")
    dt = parse_datetime(s)
    return dt


def to_decimal(value: Any):
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def synthetic_iso_code(prefix: str, platform_slug: str, remote_id: int) -> str:
    h = hashlib.sha256(f"{prefix}|{platform_slug}|{remote_id}".encode()).hexdigest().upper()
    p = (prefix or "X")[0].upper()
    return (p + h[:2])[:3]


def api_rows_as_list(raw: Any) -> list:
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        for key in ("results", "data", "items", "genres", "countries", "languages", "directors"):
            v = raw.get(key)
            if isinstance(v, list):
                return v
    return []


def int_id(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def minimum_age_from_age_rating_payload(data: dict) -> int:
    raw = data.get("minimum_age")
    if raw is not None and raw != "":
        try:
            return max(0, int(raw))
        except (TypeError, ValueError):
            pass
    text = str(data.get("title") or data.get("description") or "")
    m = re.search(r"(\d{1,2})\s*\+?", text)
    if m:
        return min(99, int(m.group(1)))
    return 0


def movie_unified_ref(movie: dict) -> str | None:
    title = str(movie.get("title") or "").strip()
    if not title:
        return None
    year_raw = movie.get("year")
    try:
        year = int(year_raw) if year_raw not in (None, "") else 0
    except (TypeError, ValueError):
        year = 0
    release_date = str(movie.get("release_date") or "").strip()
    normalized = " ".join(title.lower().split())
    return f"movie:{normalized}|{year}|{release_date}"


def series_unified_ref(ser: dict) -> str | None:
    title = str(ser.get("title") or "").strip()
    if not title:
        return None
    start_raw = ser.get("start_year")
    try:
        start_year = int(start_raw) if start_raw not in (None, "") else 0
    except (TypeError, ValueError):
        start_year = 0
    end_raw = ser.get("end_year")
    end_part = ""
    if end_raw is not None and end_raw != "":
        try:
            end_part = str(int(end_raw))
        except (TypeError, ValueError):
            end_part = str(end_raw).strip()
    ts_raw = ser.get("total_seasons")
    try:
        total_seasons = int(ts_raw) if ts_raw not in (None, "") else 0
    except (TypeError, ValueError):
        total_seasons = 0
    normalized = " ".join(title.lower().split())
    return f"series:{normalized}|{start_year}|{end_part}|{total_seasons}"
