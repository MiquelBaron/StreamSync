import requests

PLATFORMS = {
    "platform1": {"api_key": "a8f3d91c7e4b2f0a1d9c3e7b6a5f8c2d", "port": 8080},
    "platform2": {"api_key": "c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8", "port": 8081},
    "platform3": {"api_key": "a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8", "port": 8082},
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_api_key(platform):
    return PLATFORMS.get(platform, {}).get("api_key")

def get_base_url(platform):
    port = PLATFORMS.get(platform, {}).get("port")
    return f"http://localhost:{port}"

def _get(platform, endpoint):
    """Crida genèrica GET. Retorna llista o [] si falla."""
    api_key = get_api_key(platform)
    if not api_key:
        return []
    try:
        r = requests.get(
            f"{get_base_url(platform)}/{endpoint}",
            headers={"X-API-KEY": api_key},
            timeout=5
        )
        if r.status_code == 200 and r.text.strip():
            return r.json()
    except requests.RequestException as e:
        print(f"[ERROR] {platform} /{endpoint}: {e}")
    return []

def _get_all(endpoint):
    """Crida les 3 plataformes i ajunta els resultats."""
    results = []
    for platform in PLATFORMS:
        results.extend(_get(platform, endpoint))
    return results


def _get_all_by_platform(endpoint):
    """Retorna {nom_plataforma: [...]} per cada plataforma."""
    return {platform: _get(platform, endpoint) for platform in PLATFORMS}


# ── Per plataforma ─────────────────────────────────────────────────────────────

def get_movies(platform):
    return _get(platform, "movies")

def get_series(platform):
    return _get(platform, "series")

def get_directors(platform):
    return _get(platform, "directors")

def get_genres(platform):
    return _get(platform, "genres")

def get_age_ratings(platform):
    return _get(platform, "age-ratings")


def get_countries(platform):
    return _get(platform, "countries")


def get_languages(platform):
    return _get(platform, "languages")


def get_country_row(platform, pk):
    """Un país per id (per resoldre FKs si la llista completa no està disponible)."""
    for path in (f"countries/{pk}", f"country/{pk}"):
        data = _get(platform, path)
        if isinstance(data, dict) and data.get("id") is not None:
            return data
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return data[0]
    return None


def get_language_row(platform, pk):
    """Un idioma per id."""
    for path in (f"languages/{pk}", f"language/{pk}"):
        data = _get(platform, path)
        if isinstance(data, dict) and data.get("id") is not None:
            return data
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return data[0]
    return None


# ── Les 3 BD combinades ────────────────────────────────────────────────────────

def get_all_movies():
    return _get_all_by_platform("movies")

def get_all_series():
    return _get_all_by_platform("series")

def get_all_directors():
    return _get_all("directors")

def get_all_genres():
    return _get_all("genres")

def get_all_age_ratings():
    return _get_all("age-ratings")