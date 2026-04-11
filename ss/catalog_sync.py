"""
Sincronitza els models de catàleg (Movie, Series i FKs) des de ``ss.services``.

Flux (per cada clau de ``services.PLATFORMS``): es criden ``get_all_movies()`` i
``get_all_series()`` (dict per plataforma), i ``get_genres``, ``get_age_ratings``,
``get_directors`` per construir mapes d'IDs remots → instàncies locals. No es suposen
llistes globals de països/idiomes: es fa servir ``get_country_row`` / ``get_language_row``
quan cal, i si l'API no retorna fila es genera un registre sintètic estable per
``(plataforma, id_remot)``.

Cron diari (exemple): ``python manage.py sync_catalog``
"""
from __future__ import annotations

import hashlib
from datetime import date as date_cls
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import transaction
from django.utils.dateparse import parse_date, parse_datetime

from ss import services
from ss.models import AgeRating, Country, Director, Genre, Language, Movie, Platform, Series


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


def _ensure_platform(slug: str) -> Platform:
    obj, _ = Platform.objects.get_or_create(
        name=slug,
        defaults={"description": f"Plataforma sincronitzada ({slug})"},
    )
    return obj


def _upsert_country_from_row(row: dict) -> Country:
    rid = int(row["id"])
    name = str(row.get("name") or f"Country-{rid}")[:100]
    raw = str(row.get("iso_code") or row.get("code") or "").strip().upper()
    if len(raw) >= 2:
        iso = raw[:3]
    else:
        alnum = "".join(c for c in name.upper() if c.isalnum())
        iso = (alnum + "XXX")[:3] if len(alnum) >= 2 else f"K{rid % 100:02d}"[:3]
    obj, _ = Country.objects.update_or_create(iso_code=iso, defaults={"name": name})
    return obj


def _upsert_language_from_row(row: dict) -> Language:
    rid = int(row["id"])
    name = str(row.get("name") or f"Language-{rid}")[:50]
    raw = str(row.get("iso_code") or row.get("code") or "").strip().upper()
    if len(raw) >= 2:
        iso = raw[:3]
    else:
        iso = f"L{rid % 100:02d}"[:3]
    obj, _ = Language.objects.update_or_create(iso_code=iso, defaults={"name": name})
    return obj


def _synthetic_iso_code(prefix: str, platform_slug: str, remote_id: int) -> str:
    """Codi ISO 3 caràcters estable per (prefix, plataforma, id remot) sense col·lisions pràctiques."""
    h = hashlib.sha256(f"{prefix}|{platform_slug}|{remote_id}".encode()).hexdigest().upper()
    p = (prefix or "X")[0].upper()
    return (p + h[:2])[:3]


def _sync_genres_for_platform(platform_slug: str) -> dict[int, Genre]:
    rows = services.get_genres(platform_slug)
    mapping: dict[int, Genre] = {}
    for row in rows:
        if not isinstance(row, dict) or "id" not in row:
            continue
        name = row.get("name") or f"genre-{row['id']}"
        obj, _ = Genre.objects.update_or_create(
            name=name,
            defaults={"description": row.get("description") or ""},
        )
        mapping[int(row["id"])] = obj
    return mapping


def _sync_age_ratings_for_platform(platform_slug: str) -> dict[int, AgeRating]:
    rows = services.get_age_ratings(platform_slug)
    mapping: dict[int, AgeRating] = {}
    for row in rows:
        if not isinstance(row, dict) or "id" not in row:
            continue
        desc = row.get("description") or str(row["id"])
        min_age = int(row.get("minimum_age", 0))
        obj = AgeRating.objects.filter(description=desc, minimum_age=min_age).first()
        if obj is None:
            obj = AgeRating.objects.create(description=desc, minimum_age=min_age)
        mapping[int(row["id"])] = obj
    return mapping


def _sync_directors_for_platform(platform_slug: str) -> dict[int, Director]:
    rows = services.get_directors(platform_slug)
    mapping: dict[int, Director] = {}
    for row in rows:
        if not isinstance(row, dict) or "id" not in row:
            continue
        name = row.get("name") or f"director-{row['id']}"
        birth = _parse_api_date(row.get("birth_date"))
        country_str = row.get("country") or ""
        country_obj = None
        if country_str:
            iso = country_str[:3].upper()
            country_obj, _ = Country.objects.get_or_create(
                iso_code=iso,
                defaults={"name": country_str},
            )
        obj = Director.objects.filter(name=name, birth_date=birth).first()
        if obj is None:
            obj = Director.objects.create(name=name, birth_date=birth, country=country_obj)
        elif country_obj is not None:
            obj.country = country_obj
            obj.save(update_fields=["country"])
        mapping[int(row["id"])] = obj
    return mapping


def _resolve_map_fk(mapping: dict[int, Any], api_id: Any) -> Any | None:
    if api_id is None:
        return None
    try:
        key = int(api_id)
    except (TypeError, ValueError):
        return None
    return mapping.get(key)


def _resolve_country(
    platform_slug: str, api_id: Any, country_map: dict[int, Country]
) -> Country | None:
    obj = _resolve_map_fk(country_map, api_id)
    if obj is not None:
        return obj
    try:
        key = int(api_id)
    except (TypeError, ValueError):
        return None
    row = services.get_country_row(platform_slug, key)
    if row:
        obj = _upsert_country_from_row(row)
    else:
        iso = _synthetic_iso_code("C", platform_slug, key)
        obj, _ = Country.objects.get_or_create(
            iso_code=iso,
            defaults={"name": f"País (ref. {key}, {platform_slug})"},
        )
    country_map[key] = obj
    return obj


def _resolve_language(
    platform_slug: str, api_id: Any, language_map: dict[int, Language]
) -> Language | None:
    obj = _resolve_map_fk(language_map, api_id)
    if obj is not None:
        return obj
    try:
        key = int(api_id)
    except (TypeError, ValueError):
        return None
    row = services.get_language_row(platform_slug, key)
    if row:
        obj = _upsert_language_from_row(row)
    else:
        iso = _synthetic_iso_code("L", platform_slug, key)
        obj, _ = Language.objects.get_or_create(
            iso_code=iso,
            defaults={"name": f"Idioma (ref. {key}, {platform_slug})"},
        )
    language_map[key] = obj
    return obj


def sync_catalog_from_apis() -> dict[str, Any]:
    """
    Descarrega dades amb ``services.get_all_movies()``, ``get_all_series()`` i,
    per plataforma, ``get_genres`` / ``get_age_ratings`` / ``get_directors``.

    Upserta ``Genre``, ``AgeRating``, ``Country``, ``Language``, ``Director``,
    ``Movie`` i ``Series``; vincula ``Movie``/``Series`` a ``Platform`` via M2M.
    """
    stats = {
        "platforms": 0,
        "movies_upserted": 0,
        "series_upserted": 0,
        "errors": [],
    }

    movies_by_platform = services.get_all_movies()
    series_by_platform = services.get_all_series()

    with transaction.atomic():
        for platform_slug in services.PLATFORMS:
            platform_obj = _ensure_platform(platform_slug)
            stats["platforms"] += 1

            country_map: dict[int, Country] = {}
            language_map: dict[int, Language] = {}
            genre_map = _sync_genres_for_platform(platform_slug)
            age_map = _sync_age_ratings_for_platform(platform_slug)
            director_map = _sync_directors_for_platform(platform_slug)

            for movie in movies_by_platform.get(platform_slug) or []:
                if not isinstance(movie, dict) or not movie.get("title"):
                    continue
                genre = _resolve_map_fk(genre_map, movie.get("genre_id"))
                director = _resolve_map_fk(director_map, movie.get("director_id"))
                country = _resolve_country(platform_slug, movie.get("country_id"), country_map)
                language = _resolve_language(platform_slug, movie.get("language_id"), language_map)
                age_rating = _resolve_map_fk(age_map, movie.get("age_rating_id"))

                if not all([genre, director, country, language, age_rating]):
                    stats["errors"].append(
                        f"Pel·lícula '{movie.get('title')}' ({platform_slug}): FK faltant "
                        f"(genre={movie.get('genre_id')}, director={movie.get('director_id')}, "
                        f"country={movie.get('country_id')}, language={movie.get('language_id')}, "
                        f"age_rating={movie.get('age_rating_id')})."
                    )
                    continue

                obj, _ = Movie.objects.update_or_create(
                    title=movie["title"],
                    defaults={
                        "synopsis": movie.get("synopsis") or None,
                        "year": int(movie.get("year") or 0),
                        "release_date": _parse_api_date(movie.get("release_date")),
                        "rating": _to_decimal(movie.get("rating")),
                        "genre": genre,
                        "director": director,
                        "country": country,
                        "language": language,
                        "age_rating": age_rating,
                        "expires_at": _parse_api_datetime(movie.get("expires_at")),
                    },
                )
                obj.platforms.add(platform_obj)
                stats["movies_upserted"] += 1

            for ser in series_by_platform.get(platform_slug) or []:
                if not isinstance(ser, dict) or not ser.get("title"):
                    continue
                genre = _resolve_map_fk(genre_map, ser.get("genre_id"))
                director = _resolve_map_fk(director_map, ser.get("director_id"))
                country = _resolve_country(platform_slug, ser.get("country_id"), country_map)
                language = _resolve_language(platform_slug, ser.get("language_id"), language_map)
                age_rating = _resolve_map_fk(age_map, ser.get("age_rating_id"))

                if not all([genre, director, country, language, age_rating]):
                    stats["errors"].append(
                        f"Sèrie '{ser.get('title')}' ({platform_slug}): FK faltant "
                        f"(genre={ser.get('genre_id')}, director={ser.get('director_id')}, "
                        f"country={ser.get('country_id')}, language={ser.get('language_id')}, "
                        f"age_rating={ser.get('age_rating_id')})."
                    )
                    continue

                end_year = ser.get("end_year")
                if end_year is not None and end_year != "":
                    try:
                        end_year = int(end_year)
                    except (TypeError, ValueError):
                        end_year = None
                else:
                    end_year = None

                obj, _ = Series.objects.update_or_create(
                    title=ser["title"],
                    defaults={
                        "synopsis": ser.get("synopsis") or None,
                        "start_year": int(ser.get("start_year") or 0),
                        "end_year": end_year,
                        "total_seasons": int(ser.get("total_seasons") or 0),
                        "rating": _to_decimal(ser.get("rating")),
                        "genre": genre,
                        "director": director,
                        "country": country,
                        "language": language,
                        "age_rating": age_rating,
                        "expires_at": _parse_api_datetime(ser.get("expires_at")),
                    },
                )
                obj.platforms.add(platform_obj)
                stats["series_upserted"] += 1

    return stats
