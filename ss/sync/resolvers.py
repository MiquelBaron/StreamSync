"""Resolució de FKs des de payloads i placeholders de fallada."""
from __future__ import annotations

from typing import Any

from ss.models import AgeRating, Country, Director, Genre, Language

from .constants import CATALOG_REF_SOURCE
from .mappers import int_id, parse_api_date, synthetic_iso_code, to_decimal
from .upserts import (
    country_from_string_label,
    default_language,
    upsert_age_rating_nested,
    upsert_country_nested,
    upsert_director_nested,
    upsert_genre_nested,
    upsert_language_nested,
)


def resolve_genre(platform_slug: str, payload: dict, genre_map: dict[int, Genre]) -> Genre:
    g = upsert_genre_nested(platform_slug, payload.get("genre"))
    if g is not None:
        return g
    gid = int_id(payload.get("genre_id"))
    if gid is not None and gid in genre_map:
        return genre_map[gid]
    return placeholder_genre()


def resolve_director(platform_slug: str, payload: dict, director_map: dict[int, Director]) -> Director:
    d = upsert_director_nested(platform_slug, payload.get("director"))
    if d is not None:
        return d
    did = int_id(payload.get("director_id"))
    if did is not None and did in director_map:
        return director_map[did]
    return placeholder_director()


def resolve_country_for_content(
    platform_slug: str,
    payload: dict,
    country_map: dict[int, Country],
) -> Country:
    country_data = payload.get("country")
    if isinstance(country_data, dict) and country_data.get("id") is not None:
        c = upsert_country_nested(platform_slug, country_data)
        if c:
            return c
    cid = int_id(payload.get("country_id"))
    if cid is not None and cid in country_map:
        return country_map[cid]
    d = payload.get("director") or {}
    dc = d.get("country")
    if isinstance(dc, dict):
        c = upsert_country_nested(platform_slug, dc)
        if c:
            return c
    if isinstance(dc, str) and dc.strip():
        c = country_from_string_label(dc)
        if c:
            return c
    return placeholder_country()


def resolve_language(platform_slug: str, payload: dict, language_map: dict[int, Language]) -> Language:
    if isinstance(payload.get("language"), dict):
        return upsert_language_nested(platform_slug, payload["language"])
    lid = int_id(payload.get("language_id"))
    if lid is not None and lid in language_map:
        return language_map[lid]
    return default_language()


def resolve_movie_age_rating_and_decimal(
    platform_slug: str, movie: dict
) -> tuple[AgeRating | None, Any]:
    rating_raw = movie.get("rating")
    content_rating = None
    age_rating = None
    if isinstance(rating_raw, dict):
        age_rating = upsert_age_rating_nested(platform_slug, rating_raw)
    elif rating_raw is not None and rating_raw != "":
        content_rating = to_decimal(rating_raw)
    if age_rating is None and isinstance(movie.get("age_rating"), dict):
        age_rating = upsert_age_rating_nested(platform_slug, movie["age_rating"])
    return age_rating, content_rating


def resolve_age_rating_for_movie(
    platform_slug: str,
    movie: dict,
    age_map: dict[int, AgeRating],
) -> tuple[AgeRating | None, Any]:
    age_rating, rating_decimal = resolve_movie_age_rating_and_decimal(platform_slug, movie)
    if age_rating is None:
        aid = int_id(movie.get("age_rating_id"))
        if aid is not None and aid in age_map:
            age_rating = age_map[aid]
    return age_rating, rating_decimal


def resolve_age_rating_for_series(
    platform_slug: str,
    ser: dict,
    age_map: dict[int, AgeRating],
) -> AgeRating | None:
    ar = upsert_age_rating_nested(platform_slug, ser.get("age_rating")) or upsert_age_rating_nested(
        platform_slug, ser.get("rating") if isinstance(ser.get("rating"), dict) else None
    )
    if ar is not None:
        return ar
    aid = int_id(ser.get("age_rating_id"))
    if aid is not None and aid in age_map:
        return age_map[aid]
    return None


def placeholder_genre() -> Genre:
    obj, _ = Genre.objects.update_or_create(
        source_platform=CATALOG_REF_SOURCE,
        external_id=0,
        defaults={"name": "Altres", "description": "Contingut sense gènere resolt a l'API"},
    )
    return obj


def placeholder_director() -> Director:
    obj, _ = Director.objects.update_or_create(
        source_platform=CATALOG_REF_SOURCE,
        external_id=0,
        defaults={"name": "— sense director", "birth_date": None, "country": None},
    )
    return obj


def placeholder_age_rating() -> AgeRating:
    obj, _ = AgeRating.objects.update_or_create(
        source_platform=CATALOG_REF_SOURCE,
        external_id=0,
        defaults={"description": "— sense classificació", "minimum_age": 0},
    )
    return obj


def placeholder_country() -> Country:
    iso = synthetic_iso_code("P", CATALOG_REF_SOURCE, 0)
    obj, _ = Country.objects.update_or_create(
        source_platform=CATALOG_REF_SOURCE,
        external_id=0,
        defaults={"name": "— sense país", "iso_code": iso},
    )
    return obj
