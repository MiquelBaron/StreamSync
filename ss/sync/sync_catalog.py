"""
Orquestració del sync de catàleg: transacció, ordre de passos i estadístiques.
La lògica de domini viu a ``api_fetchers``, ``upserts``, ``resolvers``, ``mappers``.
"""
from __future__ import annotations

from typing import Any

from django.db import transaction
from django.utils import timezone

from ss.models import Film, Serie

from . import api_fetchers
from .mappers import movie_unified_ref, parse_api_date, parse_api_datetime, series_unified_ref, to_decimal
from .resolvers import (
    placeholder_age_rating,
    resolve_age_rating_for_movie,
    resolve_age_rating_for_series,
    resolve_country_for_content,
    resolve_director,
    resolve_genre,
    resolve_language,
)
from .upserts import (
    ensure_platform,
    merge_duplicate_films,
    merge_duplicate_series,
    merge_legacy_reference_tables,
    sync_age_ratings_from_endpoint,
    sync_countries_from_endpoint,
    sync_directors_from_endpoint,
    sync_genres_from_endpoint,
    sync_languages_from_endpoint,
)


def _init_stats() -> dict[str, Any]:
    return {
        "platforms": 0,
        "movies_upserted": 0,
        "series_upserted": 0,
        "movies_soft_deactivated": 0,
        "series_soft_deactivated": 0,
        "errors": [],
    }


def _sync_movies_for_platform(
    platform_slug: str,
    platform_obj,
    movies: list,
    maps: dict,
    now,
    seen_movie_refs: set[str],
    stats: dict[str, Any],
) -> None:
    country_map = maps["country_map"]
    language_map = maps["language_map"]
    genre_map = maps["genre_map"]
    age_map = maps["age_map"]
    director_map = maps["director_map"]

    for movie in movies or []:
        if not isinstance(movie, dict) or movie.get("id") is None:
            continue
        ext_id = int(movie["id"])
        ref = movie_unified_ref(movie)
        if ref is None:
            stats["errors"].append(f"Pel·lícula sense títol (id={ext_id}, {platform_slug}).")
            continue
        seen_movie_refs.add(ref)

        genre = resolve_genre(platform_slug, movie, genre_map)
        director = resolve_director(platform_slug, movie, director_map)
        age_rating, rating_decimal = resolve_age_rating_for_movie(platform_slug, movie, age_map)
        if age_rating is None:
            age_rating = placeholder_age_rating()

        country = resolve_country_for_content(platform_slug, movie, country_map)
        language = resolve_language(platform_slug, movie, language_map)
        if rating_decimal is None:
            rating_decimal = to_decimal(movie.get("content_rating"))

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
                "release_date": parse_api_date(movie.get("release_date")),
                "duration_minutes": duration_minutes,
                "rating": rating_decimal,
                "genre": genre,
                "director": director,
                "country": country,
                "language": language,
                "age_rating": age_rating,
                "expires_at": parse_api_datetime(movie.get("expires_at")),
                "last_seen": now,
                "is_active": True,
            },
        )
        film.platforms.add(platform_obj)
        merge_duplicate_films(film)
        stats["movies_upserted"] += 1


def _sync_series_for_platform(
    platform_slug: str,
    platform_obj,
    series: list,
    maps: dict,
    now,
    seen_series_refs: set[str],
    stats: dict[str, Any],
) -> None:
    country_map = maps["country_map"]
    language_map = maps["language_map"]
    genre_map = maps["genre_map"]
    age_map = maps["age_map"]
    director_map = maps["director_map"]

    for ser in series or []:
        if not isinstance(ser, dict) or ser.get("id") is None:
            continue
        ext_id = int(ser["id"])
        ref = series_unified_ref(ser)
        if ref is None:
            stats["errors"].append(f"Sèrie sense títol (id={ext_id}, {platform_slug}).")
            continue
        seen_series_refs.add(ref)

        genre = resolve_genre(platform_slug, ser, genre_map)
        director = resolve_director(platform_slug, ser, director_map)
        age_rating = resolve_age_rating_for_series(platform_slug, ser, age_map)
        if age_rating is None:
            age_rating = placeholder_age_rating()

        country = resolve_country_for_content(platform_slug, ser, country_map)
        language = resolve_language(platform_slug, ser, language_map)

        base_title = str(ser.get("title") or "").strip()
        if not base_title:
            stats["errors"].append(f"Sèrie sense títol (id={ext_id}, {platform_slug}).")
            continue
        title = base_title[:255]

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
                "rating": to_decimal(ser.get("rating")) if not isinstance(ser.get("rating"), dict) else None,
                "genre": genre,
                "director": director,
                "country": country,
                "language": language,
                "age_rating": age_rating,
                "expires_at": parse_api_datetime(ser.get("expires_at")),
                "last_seen": now,
                "is_active": True,
            },
        )
        serie.platforms.add(platform_obj)
        merge_duplicate_series(serie)
        stats["series_upserted"] += 1


def _deactivate_missing(seen_movie_refs: set[str], seen_series_refs: set[str], stats: dict[str, Any]) -> None:
    stats["movies_soft_deactivated"] = Film.objects.filter(sync_external_ref__isnull=False).exclude(
        sync_external_ref__in=seen_movie_refs
    ).filter(is_active=True).update(is_active=False)
    stats["series_soft_deactivated"] = Serie.objects.filter(sync_external_ref__isnull=False).exclude(
        sync_external_ref__in=seen_series_refs
    ).filter(is_active=True).update(is_active=False)


def _sync_platform(
    platform_slug: str,
    data: dict[str, dict],
    now,
    seen_movie_refs: set[str],
    seen_series_refs: set[str],
    stats: dict[str, Any],
) -> None:
    platform_obj = ensure_platform(platform_slug)
    stats["platforms"] += 1
    country_map = sync_countries_from_endpoint(platform_slug)
    maps = {
        "country_map": country_map,
        "language_map": sync_languages_from_endpoint(platform_slug),
        "genre_map": sync_genres_from_endpoint(platform_slug),
        "age_map": sync_age_ratings_from_endpoint(platform_slug),
        "director_map": sync_directors_from_endpoint(platform_slug, country_map),
    }
    _sync_movies_for_platform(
        platform_slug,
        platform_obj,
        data["movies"].get(platform_slug) or [],
        maps,
        now,
        seen_movie_refs,
        stats,
    )
    _sync_series_for_platform(
        platform_slug,
        platform_obj,
        data["series"].get(platform_slug) or [],
        maps,
        now,
        seen_series_refs,
        stats,
    )


def sync_catalog_from_apis() -> dict[str, Any]:
    stats = _init_stats()
    now = timezone.now()
    data = api_fetchers.fetch_all()
    seen_movie_refs: set[str] = set()
    seen_series_refs: set[str] = set()

    with transaction.atomic():
        merge_legacy_reference_tables()
        for platform_slug in api_fetchers.get_platforms():
            _sync_platform(platform_slug, data, now, seen_movie_refs, seen_series_refs, stats)
        _deactivate_missing(seen_movie_refs, seen_series_refs, stats)

    return stats
