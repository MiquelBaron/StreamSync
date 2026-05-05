"""
Sincronitza el catàleg des de ``ss.catalog_api`` (OpenAPI Movies API v1).

Alineació amb l'esquema publicat:
- ``Genre``: ``id``, ``description`` (sense ``name``); el nom local es deriva de ``description``.
- ``AgeRating``: ``id``, ``title`` (sense ``minimum_age`` obligatori); es mapa ``title`` →
  ``AgeRating.description`` i s'intenta extreure l'edat mínima del text si cal.
- ``Movie.rating``: pot ser objecte (classificació) o número (valoració de contingut);
  objecte → ``AgeRating``; número → ``Content.rating``.
- ``Movie``: ``duration_minutes`` es persisteix a ``Film.duration_minutes``.
- ``Serie``: només ``id`` i ``title`` al schema; la resta de FKs es resolen amb placeholders
  o mapes dels endpoints quan hi hagi ``*_id``.

Flux per plataforma: endpoints de referència → ``movies``/``series`` → mirall suau ``is_active``.
"""
from __future__ import annotations

import hashlib
import re
from datetime import date as date_cls
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from ss import catalog_api as services
from ss.models import AgeRating, Content, Country, Director, Film, Genre, Language, Platform, Serie


def _parse_api_date(value: Any):
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


def _parse_api_datetime(value: Any):
    if value is None or value == "":
        return None
    if hasattr(value, "year") and not isinstance(value, str):
        return value
    s = str(value).replace("Z", "+00:00")
    dt = parse_datetime(s)
    return dt


def _to_decimal(value: Any):
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _synthetic_iso_code(prefix: str, platform_slug: str, remote_id: int) -> str:
    h = hashlib.sha256(f"{prefix}|{platform_slug}|{remote_id}".encode()).hexdigest().upper()
    p = (prefix or "X")[0].upper()
    return (p + h[:2])[:3]


def _ensure_platform(slug: str) -> Platform:
    obj, _ = Platform.objects.get_or_create(
        name=slug,
        defaults={"description": f"Plataforma sincronitzada ({slug})"},
    )
    return obj


def _default_language() -> Language:
    obj, _ = Language.objects.get_or_create(
        iso_code="und",
        defaults={"name": "Desconegut", "source_platform": "", "external_id": None},
    )
    return obj


def _upsert_country_nested(platform_slug: str, data: dict | None) -> Country | None:
    if not data or not isinstance(data, dict) or data.get("id") is None:
        return None
    rid = int(data["id"])
    name = str(data.get("name") or f"Country-{rid}")[:100]
    raw = str(data.get("iso_code") or data.get("code") or "").strip().upper()
    if len(raw) >= 3:
        iso = raw[:3]
    else:
        iso = _synthetic_iso_code("C", platform_slug, rid)
    existing = Country.objects.filter(iso_code=iso).exclude(
        source_platform=platform_slug, external_id=rid
    ).first()
    if existing:
        iso = _synthetic_iso_code("C", platform_slug, rid)
    obj, _ = Country.objects.update_or_create(
        source_platform=platform_slug,
        external_id=rid,
        defaults={"name": name, "iso_code": iso},
    )
    return obj


def _upsert_language_nested(platform_slug: str, data: dict | None) -> Language:
    if not data or not isinstance(data, dict) or data.get("id") is None:
        return _default_language()
    rid = int(data["id"])
    name = str(data.get("name") or f"Language-{rid}")[:50]
    raw = str(data.get("iso_code") or data.get("code") or "").strip().upper()
    if len(raw) >= 3:
        iso = raw[:3]
    else:
        iso = _synthetic_iso_code("L", platform_slug, rid)
    if Language.objects.filter(iso_code=iso).exclude(
        source_platform=platform_slug, external_id=rid
    ).exists():
        iso = _synthetic_iso_code("L", platform_slug, rid)
    obj, _ = Language.objects.update_or_create(
        source_platform=platform_slug,
        external_id=rid,
        defaults={"name": name, "iso_code": iso},
    )
    return obj


def _upsert_genre_nested(platform_slug: str, data: dict | None) -> Genre | None:
    """OpenAPI ``Genre``: ``id``, ``description`` (camp ``name`` opcional al payload)."""
    if not data or not isinstance(data, dict) or data.get("id") is None:
        return None
    rid = int(data["id"])
    raw_desc = data.get("description")
    desc_str = str(raw_desc).strip() if raw_desc is not None else ""
    name = str(data.get("name") or desc_str or f"Gènere-{rid}")[:100]
    desc = desc_str or None
    obj, _ = Genre.objects.update_or_create(
        source_platform=platform_slug,
        external_id=rid,
        defaults={"name": name, "description": desc},
    )
    return obj


def _minimum_age_from_age_rating_payload(data: dict) -> int:
    """OpenAPI no exigeix ``minimum_age``; s'utilitza el camp si ve, o es treu del ``title``."""
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


def _upsert_age_rating_nested(platform_slug: str, data: dict | None) -> AgeRating | None:
    """OpenAPI ``AgeRating``: ``id``, ``title`` (el títol es guarda a ``description`` local)."""
    if not data or not isinstance(data, dict) or data.get("id") is None:
        return None
    rid = int(data["id"])
    desc = str(data.get("title") or data.get("description") or f"Classificació-{rid}")[:50]
    min_age = _minimum_age_from_age_rating_payload(data)
    obj, _ = AgeRating.objects.update_or_create(
        source_platform=platform_slug,
        external_id=rid,
        defaults={"description": desc, "minimum_age": min_age},
    )
    return obj


def _country_from_string_label(label: str) -> Country | None:
    """País llegat com a text curt (API legacy); ``iso_code`` únic 3 caràcters."""
    if not label or not str(label).strip():
        return None
    s = str(label).strip()
    iso = s[:3].upper().ljust(3, "X")[:3]
    obj, _ = Country.objects.get_or_create(
        iso_code=iso,
        defaults={"name": s[:100], "source_platform": "", "external_id": None},
    )
    return obj


def _upsert_director_nested(platform_slug: str, data: dict | None) -> Director | None:
    if not data or not isinstance(data, dict) or data.get("id") is None:
        return None
    rid = int(data["id"])
    c_raw = data.get("country")
    if isinstance(c_raw, dict):
        country_obj = _upsert_country_nested(platform_slug, c_raw)
    elif isinstance(c_raw, str) and c_raw.strip():
        country_obj = _country_from_string_label(c_raw)
    else:
        country_obj = None
    obj, _ = Director.objects.update_or_create(
        source_platform=platform_slug,
        external_id=rid,
        defaults={
            "name": str(data.get("name") or f"Director-{rid}")[:150],
            "birth_date": _parse_api_date(data.get("birth_date")),
            "country": country_obj,
        },
    )
    return obj


def _api_rows_as_list(raw: Any) -> list:
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


def _sync_countries_from_endpoint(platform_slug: str) -> dict[int, Country]:
    mapping: dict[int, Country] = {}
    for row in _api_rows_as_list(services.get_countries(platform_slug)):
        if not isinstance(row, dict) or row.get("id") is None:
            continue
        c = _upsert_country_nested(platform_slug, row)
        if c:
            mapping[int(row["id"])] = c
    return mapping


def _sync_languages_from_endpoint(platform_slug: str) -> dict[int, Language]:
    mapping: dict[int, Language] = {}
    for row in _api_rows_as_list(services.get_languages(platform_slug)):
        if not isinstance(row, dict) or row.get("id") is None:
            continue
        lang = _upsert_language_nested(platform_slug, row)
        mapping[int(row["id"])] = lang
    return mapping


def _sync_genres_from_endpoint(platform_slug: str) -> dict[int, Genre]:
    mapping: dict[int, Genre] = {}
    for row in _api_rows_as_list(services.get_genres(platform_slug)):
        if not isinstance(row, dict) or row.get("id") is None:
            continue
        g = _upsert_genre_nested(platform_slug, row)
        if g:
            mapping[int(row["id"])] = g
    return mapping


def _sync_age_ratings_from_endpoint(platform_slug: str) -> dict[int, AgeRating]:
    mapping: dict[int, AgeRating] = {}
    for row in _api_rows_as_list(services.get_age_ratings(platform_slug)):
        if not isinstance(row, dict) or row.get("id") is None:
            continue
        ar = _upsert_age_rating_nested(platform_slug, row)
        if ar:
            mapping[int(row["id"])] = ar
    return mapping


def _sync_directors_from_endpoint(platform_slug: str, country_map: dict[int, Country]) -> dict[int, Director]:
    mapping: dict[int, Director] = {}
    for row in _api_rows_as_list(services.get_directors(platform_slug)):
        if not isinstance(row, dict) or row.get("id") is None:
            continue
        rid = int(row["id"])
        country_obj = None
        cid = row.get("country_id")
        if cid is not None:
            try:
                country_obj = country_map.get(int(cid))
            except (TypeError, ValueError):
                pass
        if country_obj is None:
            c_raw = row.get("country")
            if isinstance(c_raw, dict):
                country_obj = _upsert_country_nested(platform_slug, c_raw)
            elif isinstance(c_raw, str) and c_raw.strip():
                country_obj = _country_from_string_label(c_raw)
        obj, _ = Director.objects.update_or_create(
            source_platform=platform_slug,
            external_id=rid,
            defaults={
                "name": str(row.get("name") or f"Director-{rid}")[:150],
                "birth_date": _parse_api_date(row.get("birth_date")),
                "country": country_obj,
            },
        )
        mapping[rid] = obj
    return mapping


def _int_id(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _resolve_genre(platform_slug: str, payload: dict, genre_map: dict[int, Genre]) -> Genre:
    g = _upsert_genre_nested(platform_slug, payload.get("genre"))
    if g is not None:
        return g
    gid = _int_id(payload.get("genre_id"))
    if gid is not None and gid in genre_map:
        return genre_map[gid]
    return _placeholder_genre(platform_slug)


def _resolve_director(platform_slug: str, payload: dict, director_map: dict[int, Director]) -> Director:
    d = _upsert_director_nested(platform_slug, payload.get("director"))
    if d is not None:
        return d
    did = _int_id(payload.get("director_id"))
    if did is not None and did in director_map:
        return director_map[did]
    return _placeholder_director(platform_slug)


def _resolve_country_for_content(
    platform_slug: str,
    payload: dict,
    country_map: dict[int, Country],
) -> Country:
    country_data = payload.get("country")
    if isinstance(country_data, dict) and country_data.get("id") is not None:
        c = _upsert_country_nested(platform_slug, country_data)
        if c:
            return c
    cid = _int_id(payload.get("country_id"))
    if cid is not None and cid in country_map:
        return country_map[cid]
    d = payload.get("director") or {}
    dc = d.get("country")
    if isinstance(dc, dict):
        c = _upsert_country_nested(platform_slug, dc)
        if c:
            return c
    if isinstance(dc, str) and dc.strip():
        c = _country_from_string_label(dc)
        if c:
            return c
    return _placeholder_country(platform_slug)


def _resolve_language(platform_slug: str, payload: dict, language_map: dict[int, Language]) -> Language:
    if isinstance(payload.get("language"), dict):
        return _upsert_language_nested(platform_slug, payload["language"])
    lid = _int_id(payload.get("language_id"))
    if lid is not None and lid in language_map:
        return language_map[lid]
    return _default_language()


def _resolve_age_rating_for_movie(
    platform_slug: str,
    movie: dict,
    age_map: dict[int, AgeRating],
) -> tuple[AgeRating | None, Any]:
    age_rating, rating_decimal = _resolve_movie_age_rating_and_decimal(platform_slug, movie)
    if age_rating is None:
        aid = _int_id(movie.get("age_rating_id"))
        if aid is not None and aid in age_map:
            age_rating = age_map[aid]
    return age_rating, rating_decimal


def _resolve_age_rating_for_series(
    platform_slug: str,
    ser: dict,
    age_map: dict[int, AgeRating],
) -> AgeRating | None:
    ar = _upsert_age_rating_nested(platform_slug, ser.get("age_rating")) or _upsert_age_rating_nested(
        platform_slug, ser.get("rating") if isinstance(ser.get("rating"), dict) else None
    )
    if ar is not None:
        return ar
    aid = _int_id(ser.get("age_rating_id"))
    if aid is not None and aid in age_map:
        return age_map[aid]
    return None


def _placeholder_genre(platform_slug: str) -> Genre:
    obj, _ = Genre.objects.update_or_create(
        source_platform=platform_slug,
        external_id=0,
        defaults={"name": "Altres", "description": "Contingut sense gènere resolt a l'API"},
    )
    return obj


def _placeholder_director(platform_slug: str) -> Director:
    obj, _ = Director.objects.update_or_create(
        source_platform=platform_slug,
        external_id=0,
        defaults={"name": "— sense director", "birth_date": None, "country": None},
    )
    return obj


def _placeholder_age_rating(platform_slug: str) -> AgeRating:
    obj, _ = AgeRating.objects.update_or_create(
        source_platform=platform_slug,
        external_id=0,
        defaults={"description": "— sense classificació", "minimum_age": 0},
    )
    return obj


def _placeholder_country(platform_slug: str) -> Country:
    iso = _synthetic_iso_code("P", platform_slug, 0)
    obj, _ = Country.objects.update_or_create(
        source_platform=platform_slug,
        external_id=0,
        defaults={"name": "— sense país", "iso_code": iso},
    )
    return obj


def _unique_title_for_content(base: str, sync_ref: str) -> str:
    t = (base or "Sense títol").strip()[:240]
    if Content.objects.filter(title=t).exclude(sync_external_ref=sync_ref).exists():
        suffix = f" [{sync_ref}]"
        t = ((base or "Sense títol").strip()[: 255 - len(suffix)]) + suffix
    return t[:255]


def _resolve_movie_age_rating_and_decimal(
    platform_slug: str, movie: dict
) -> tuple[AgeRating | None, Any]:
    """OpenAPI pot definir ``rating`` com a número o com a objecte AgeRating."""
    rating_raw = movie.get("rating")
    content_rating = None
    age_rating = None
    if isinstance(rating_raw, dict):
        age_rating = _upsert_age_rating_nested(platform_slug, rating_raw)
    elif rating_raw is not None and rating_raw != "":
        content_rating = _to_decimal(rating_raw)
    if age_rating is None and isinstance(movie.get("age_rating"), dict):
        age_rating = _upsert_age_rating_nested(platform_slug, movie["age_rating"])
    return age_rating, content_rating


def _movie_unified_ref(movie: dict) -> str | None:
    """Genera una referència estable perquè la mateixa pel·lícula no es dupliqui per plataforma."""
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


def _merge_duplicate_films(film: Film):
    """Fusiona possibles duplicats deixant una sola instància i acumulant plataformes."""
    duplicates = Film.objects.filter(title=film.title, year=film.year).exclude(pk=film.pk).prefetch_related("platforms")
    for dup in duplicates:
        film.platforms.add(*dup.platforms.all())
        dup.delete()


def sync_catalog_from_apis() -> dict[str, Any]:
    stats: dict[str, Any] = {
        "platforms": 0,
        "movies_upserted": 0,
        "series_upserted": 0,
        "movies_soft_deactivated": 0,
        "series_soft_deactivated": 0,
        "errors": [],
    }
    now = timezone.now()
    movies_by_platform = services.get_all_movies()
    series_by_platform = services.get_all_series()
    seen_movie_refs: set[str] = set()
    seen_series_refs: set[str] = set()

    with transaction.atomic():
        for platform_slug in services.PLATFORMS:
            platform_obj = _ensure_platform(platform_slug)
            stats["platforms"] += 1

            country_map = _sync_countries_from_endpoint(platform_slug)
            language_map = _sync_languages_from_endpoint(platform_slug)
            genre_map = _sync_genres_from_endpoint(platform_slug)
            age_map = _sync_age_ratings_from_endpoint(platform_slug)
            director_map = _sync_directors_from_endpoint(platform_slug, country_map)

            for movie in movies_by_platform.get(platform_slug) or []:
                if not isinstance(movie, dict) or movie.get("id") is None:
                    continue
                ext_id = int(movie["id"])
                ref = _movie_unified_ref(movie)
                if ref is None:
                    stats["errors"].append(f"Pel·lícula sense títol (id={ext_id}, {platform_slug}).")
                    continue
                seen_movie_refs.add(ref)

                genre = _resolve_genre(platform_slug, movie, genre_map)
                director = _resolve_director(platform_slug, movie, director_map)
                age_rating, rating_decimal = _resolve_age_rating_for_movie(platform_slug, movie, age_map)
                if age_rating is None:
                    age_rating = _placeholder_age_rating(platform_slug)

                country = _resolve_country_for_content(platform_slug, movie, country_map)
                language = _resolve_language(platform_slug, movie, language_map)
                if rating_decimal is None:
                    rating_decimal = _to_decimal(movie.get("content_rating"))

                base_title = str(movie.get("title") or "").strip()
                if not base_title:
                    stats["errors"].append(f"Pel·lícula sense títol (id={ext_id}, {platform_slug}).")
                    continue
                title = base_title[:255]

                dm_raw = movie.get("duration_minutes")
                duration_minutes = None
                if dm_raw is not None and dm_raw != "":
                    try:
                        duration_minutes = max(0, int(dm_raw))
                    except (TypeError, ValueError):
                        duration_minutes = None

                film, _ = Film.objects.update_or_create(
                    sync_external_ref=ref,
                    defaults={
                        "title": title,
                        "synopsis": movie.get("synopsis") or None,
                        "year": int(movie.get("year") or 0),
                        "release_date": _parse_api_date(movie.get("release_date")),
                        "duration_minutes": duration_minutes,
                        "rating": rating_decimal,
                        "genre": genre,
                        "director": director,
                        "country": country,
                        "language": language,
                        "age_rating": age_rating,
                        "expires_at": _parse_api_datetime(movie.get("expires_at")),
                        "last_seen": now,
                        "is_active": True,
                    },
                )
                film.platforms.add(platform_obj)
                _merge_duplicate_films(film)
                stats["movies_upserted"] += 1

            for ser in series_by_platform.get(platform_slug) or []:
                if not isinstance(ser, dict) or ser.get("id") is None:
                    continue
                ext_id = int(ser["id"])
                ref = f"{platform_slug}:series:{ext_id}"
                seen_series_refs.add(ref)

                genre = _resolve_genre(platform_slug, ser, genre_map)
                director = _resolve_director(platform_slug, ser, director_map)
                age_rating = _resolve_age_rating_for_series(platform_slug, ser, age_map)
                if age_rating is None:
                    age_rating = _placeholder_age_rating(platform_slug)

                country = _resolve_country_for_content(platform_slug, ser, country_map)
                language = _resolve_language(platform_slug, ser, language_map)

                base_title = str(ser.get("title") or "").strip()
                if not base_title:
                    stats["errors"].append(f"Sèrie sense títol (id={ext_id}, {platform_slug}).")
                    continue
                title = _unique_title_for_content(base_title, ref)

                end_year = ser.get("end_year")
                if end_year is not None and end_year != "":
                    try:
                        end_year = int(end_year)
                    except (TypeError, ValueError):
                        end_year = None
                else:
                    end_year = None

                serie, _ = Serie.objects.update_or_create(
                    sync_external_ref=ref,
                    defaults={
                        "title": title,
                        "synopsis": ser.get("synopsis") or None,
                        "start_year": int(ser.get("start_year") or 0),
                        "end_year": end_year,
                        "total_seasons": int(ser.get("total_seasons") or 0),
                        "rating": _to_decimal(ser.get("rating")) if not isinstance(ser.get("rating"), dict) else None,
                        "genre": genre,
                        "director": director,
                        "country": country,
                        "language": language,
                        "age_rating": age_rating,
                        "expires_at": _parse_api_datetime(ser.get("expires_at")),
                        "last_seen": now,
                        "is_active": True,
                    },
                )
                serie.platforms.set([platform_obj])
                stats["series_upserted"] += 1

        stats["movies_soft_deactivated"] = Film.objects.filter(sync_external_ref__isnull=False).exclude(
            sync_external_ref__in=seen_movie_refs
        ).filter(is_active=True).update(is_active=False)
        stats["series_soft_deactivated"] = Serie.objects.filter(sync_external_ref__isnull=False).exclude(
            sync_external_ref__in=seen_series_refs
        ).filter(is_active=True).update(is_active=False)

    return stats
