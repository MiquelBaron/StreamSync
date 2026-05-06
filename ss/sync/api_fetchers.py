"""Crides HTTP/RPC cap a ``ss.catalog_api`` (una capa prima)."""
from ss import catalog_api as services

from .mappers import api_rows_as_list


def get_platforms() -> list[str]:
    return list(services.PLATFORMS)


def fetch_all() -> dict[str, dict]:
    """Retorna ``movies`` i ``series`` per plataforma (mateix contract que ``get_all_*``)."""
    return {
        "movies": services.get_all_movies(),
        "series": services.get_all_series(),
    }


def iter_country_rows(platform: str):
    return api_rows_as_list(services.get_countries(platform))


def iter_language_rows(platform: str):
    return api_rows_as_list(services.get_languages(platform))


def iter_genre_rows(platform: str):
    return api_rows_as_list(services.get_genres(platform))


def iter_age_rating_rows(platform: str):
    return api_rows_as_list(services.get_age_ratings(platform))


def iter_director_rows(platform: str):
    return api_rows_as_list(services.get_directors(platform))
