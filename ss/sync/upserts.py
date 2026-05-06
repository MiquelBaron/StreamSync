"""Escriptura a BD: upserts, sincronització per endpoint, fusió de duplicats."""
from __future__ import annotations

from django.db import IntegrityError

from ss.models import (
    AgeRating,
    Content,
    ContentConsumer,
    Country,
    Director,
    Film,
    Genre,
    Language,
    Platform,
    Serie,
    Visualization,
)

from . import api_fetchers
from .constants import CATALOG_REF_SOURCE
from .mappers import parse_api_date, synthetic_iso_code


def ensure_platform(slug: str) -> Platform:
    obj, _ = Platform.objects.get_or_create(
        name=slug,
        defaults={"description": f"Plataforma sincronitzada ({slug})"},
    )
    return obj


def default_language() -> Language:
    obj, _ = Language.objects.get_or_create(
        iso_code="und",
        defaults={"name": "Desconegut", "source_platform": "", "external_id": None},
    )
    return obj


def upsert_country_nested(platform_slug: str, data: dict | None) -> Country | None:
    if not data or not isinstance(data, dict) or data.get("id") is None:
        return None
    rid = int(data["id"])
    name = str(data.get("name") or f"Country-{rid}")[:100]
    raw = str(data.get("iso_code") or data.get("code") or "").strip().upper()
    if len(raw) >= 3:
        iso = raw[:3]
    else:
        iso = synthetic_iso_code("C", CATALOG_REF_SOURCE, rid)
    existing = Country.objects.filter(iso_code=iso).exclude(
        source_platform=CATALOG_REF_SOURCE, external_id=rid
    ).first()
    if existing:
        iso = synthetic_iso_code("C", CATALOG_REF_SOURCE, rid)
    obj, _ = Country.objects.update_or_create(
        source_platform=CATALOG_REF_SOURCE,
        external_id=rid,
        defaults={"name": name, "iso_code": iso},
    )
    return obj


def upsert_language_nested(platform_slug: str, data: dict | None) -> Language:
    if not data or not isinstance(data, dict) or data.get("id") is None:
        return default_language()
    rid = int(data["id"])
    name = str(data.get("name") or f"Language-{rid}")[:50]
    raw = str(data.get("iso_code") or data.get("code") or "").strip().upper()
    if len(raw) >= 3:
        iso = raw[:3]
    else:
        iso = synthetic_iso_code("L", CATALOG_REF_SOURCE, rid)
    if Language.objects.filter(iso_code=iso).exclude(
        source_platform=CATALOG_REF_SOURCE, external_id=rid
    ).exists():
        iso = synthetic_iso_code("L", CATALOG_REF_SOURCE, rid)
    obj, _ = Language.objects.update_or_create(
        source_platform=CATALOG_REF_SOURCE,
        external_id=rid,
        defaults={"name": name, "iso_code": iso},
    )
    return obj


def upsert_genre_nested(platform_slug: str, data: dict | None) -> Genre | None:
    if not data or not isinstance(data, dict) or data.get("id") is None:
        return None
    rid = int(data["id"])
    raw_desc = data.get("description")
    desc_str = str(raw_desc).strip() if raw_desc is not None else ""
    name = str(data.get("name") or desc_str or f"Gènere-{rid}")[:100]
    desc = desc_str or None
    obj, _ = Genre.objects.update_or_create(
        source_platform=CATALOG_REF_SOURCE,
        external_id=rid,
        defaults={"name": name, "description": desc},
    )
    return obj


def upsert_age_rating_nested(platform_slug: str, data: dict | None) -> AgeRating | None:
    from .mappers import minimum_age_from_age_rating_payload

    if not data or not isinstance(data, dict) or data.get("id") is None:
        return None
    rid = int(data["id"])
    desc = str(data.get("title") or data.get("description") or f"Classificació-{rid}")[:50]
    min_age = minimum_age_from_age_rating_payload(data)
    obj, _ = AgeRating.objects.update_or_create(
        source_platform=CATALOG_REF_SOURCE,
        external_id=rid,
        defaults={"description": desc, "minimum_age": min_age},
    )
    return obj


def country_from_string_label(label: str) -> Country | None:
    if not label or not str(label).strip():
        return None
    s = str(label).strip()
    iso = s[:3].upper().ljust(3, "X")[:3]
    obj, _ = Country.objects.get_or_create(
        iso_code=iso,
        defaults={"name": s[:100], "source_platform": "", "external_id": None},
    )
    return obj


def upsert_director_nested(platform_slug: str, data: dict | None) -> Director | None:
    if not data or not isinstance(data, dict) or data.get("id") is None:
        return None
    rid = int(data["id"])
    c_raw = data.get("country")
    if isinstance(c_raw, dict):
        country_obj = upsert_country_nested(platform_slug, c_raw)
    elif isinstance(c_raw, str) and c_raw.strip():
        country_obj = country_from_string_label(c_raw)
    else:
        country_obj = None
    obj, _ = Director.objects.update_or_create(
        source_platform=CATALOG_REF_SOURCE,
        external_id=rid,
        defaults={
            "name": str(data.get("name") or f"Director-{rid}")[:150],
            "birth_date": parse_api_date(data.get("birth_date")),
            "country": country_obj,
        },
    )
    return obj


def sync_countries_from_endpoint(platform_slug: str) -> dict[int, Country]:
    mapping: dict[int, Country] = {}
    for row in api_fetchers.iter_country_rows(platform_slug):
        if not isinstance(row, dict) or row.get("id") is None:
            continue
        c = upsert_country_nested(platform_slug, row)
        if c:
            mapping[int(row["id"])] = c
    return mapping


def sync_languages_from_endpoint(platform_slug: str) -> dict[int, Language]:
    mapping: dict[int, Language] = {}
    for row in api_fetchers.iter_language_rows(platform_slug):
        if not isinstance(row, dict) or row.get("id") is None:
            continue
        lang = upsert_language_nested(platform_slug, row)
        mapping[int(row["id"])] = lang
    return mapping


def sync_genres_from_endpoint(platform_slug: str) -> dict[int, Genre]:
    mapping: dict[int, Genre] = {}
    for row in api_fetchers.iter_genre_rows(platform_slug):
        if not isinstance(row, dict) or row.get("id") is None:
            continue
        g = upsert_genre_nested(platform_slug, row)
        if g:
            mapping[int(row["id"])] = g
    return mapping


def sync_age_ratings_from_endpoint(platform_slug: str) -> dict[int, AgeRating]:
    mapping: dict[int, AgeRating] = {}
    for row in api_fetchers.iter_age_rating_rows(platform_slug):
        if not isinstance(row, dict) or row.get("id") is None:
            continue
        ar = upsert_age_rating_nested(platform_slug, row)
        if ar:
            mapping[int(row["id"])] = ar
    return mapping


def sync_directors_from_endpoint(platform_slug: str, country_map: dict[int, Country]) -> dict[int, Director]:
    mapping: dict[int, Director] = {}
    for row in api_fetchers.iter_director_rows(platform_slug):
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
                country_obj = upsert_country_nested(platform_slug, c_raw)
            elif isinstance(c_raw, str) and c_raw.strip():
                country_obj = country_from_string_label(c_raw)
        obj, _ = Director.objects.update_or_create(
            source_platform=CATALOG_REF_SOURCE,
            external_id=rid,
            defaults={
                "name": str(row.get("name") or f"Director-{rid}")[:150],
                "birth_date": parse_api_date(row.get("birth_date")),
                "country": country_obj,
            },
        )
        mapping[rid] = obj
    return mapping


def merge_duplicate_films(film: Film):
    duplicates = Film.objects.filter(title=film.title, year=film.year).exclude(pk=film.pk).prefetch_related("platforms")
    for dup in duplicates:
        film.platforms.add(*dup.platforms.all())
        dup.delete()


def merge_duplicate_series(serie: Serie):
    duplicates = (
        Serie.objects.filter(title=serie.title, start_year=serie.start_year)
        .exclude(pk=serie.pk)
        .prefetch_related("platforms")
    )
    for dup in duplicates:
        serie.platforms.add(*dup.platforms.all())
        dup.delete()


def merge_legacy_reference_tables() -> None:
    for old in list(Country.objects.filter(external_id__isnull=False).exclude(source_platform=CATALOG_REF_SOURCE)):
        try:
            canon, _ = Country.objects.update_or_create(
                source_platform=CATALOG_REF_SOURCE,
                external_id=old.external_id,
                defaults={"name": old.name, "iso_code": old.iso_code},
            )
        except IntegrityError:
            canon = (
                Country.objects.filter(source_platform=CATALOG_REF_SOURCE, external_id=old.external_id).first()
                or Country.objects.filter(iso_code=old.iso_code).first()
            )
            if canon is None:
                continue
        if old.pk == canon.pk:
            continue
        Content.objects.filter(country_id=old.pk).update(country_id=canon.pk)
        Director.objects.filter(country_id=old.pk).update(country_id=canon.pk)
        old.delete()

    for old in list(Language.objects.filter(external_id__isnull=False).exclude(source_platform=CATALOG_REF_SOURCE)):
        try:
            canon, _ = Language.objects.update_or_create(
                source_platform=CATALOG_REF_SOURCE,
                external_id=old.external_id,
                defaults={"name": old.name, "iso_code": old.iso_code},
            )
        except IntegrityError:
            canon = (
                Language.objects.filter(source_platform=CATALOG_REF_SOURCE, external_id=old.external_id).first()
                or Language.objects.filter(iso_code=old.iso_code).first()
            )
            if canon is None:
                continue
        if old.pk == canon.pk:
            continue
        Content.objects.filter(language_id=old.pk).update(language_id=canon.pk)
        old.delete()

    for old in list(Director.objects.filter(external_id__isnull=False).exclude(source_platform=CATALOG_REF_SOURCE)):
        canon, _ = Director.objects.update_or_create(
            source_platform=CATALOG_REF_SOURCE,
            external_id=old.external_id,
            defaults={
                "name": old.name,
                "birth_date": old.birth_date,
                "country_id": old.country_id,
            },
        )
        if old.pk == canon.pk:
            continue
        Content.objects.filter(director_id=old.pk).update(director_id=canon.pk)
        old.delete()

    for old in list(Genre.objects.filter(external_id__isnull=False).exclude(source_platform=CATALOG_REF_SOURCE)):
        canon, _ = Genre.objects.update_or_create(
            source_platform=CATALOG_REF_SOURCE,
            external_id=old.external_id,
            defaults={"name": old.name, "description": old.description},
        )
        if old.pk == canon.pk:
            continue
        Content.objects.filter(genre_id=old.pk).update(genre_id=canon.pk)
        Visualization.objects.filter(genre_id=old.pk).update(genre_id=canon.pk)
        for cc in ContentConsumer.objects.filter(preferred_genres=old):
            cc.preferred_genres.remove(old)
            if not cc.preferred_genres.filter(pk=canon.pk).exists():
                cc.preferred_genres.add(canon)
        old.delete()

    for old in list(AgeRating.objects.filter(external_id__isnull=False).exclude(source_platform=CATALOG_REF_SOURCE)):
        canon, _ = AgeRating.objects.update_or_create(
            source_platform=CATALOG_REF_SOURCE,
            external_id=old.external_id,
            defaults={"description": old.description, "minimum_age": old.minimum_age},
        )
        if old.pk == canon.pk:
            continue
        Content.objects.filter(age_rating_id=old.pk).update(age_rating_id=canon.pk)
        old.delete()
