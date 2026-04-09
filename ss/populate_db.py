# ss/scripts/populate_db.py
import os
import django
import random
from datetime import datetime, timedelta

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ss.settings")
django.setup()

from ss.models import Platform, Country, Genre, Director, AgeRating, Language, Movie, Series

# -------------------------------
# Crear plataformas
# -------------------------------
platforms = ["Netflix", "HBO", "Disney+"]
platform_objs = []
for name in platforms:
    p, _ = Platform.objects.get_or_create(name=name)
    platform_objs.append(p)

# -------------------------------
# Crear países
# -------------------------------
countries = [("USA", "USA"), ("Canada", "CAN"), ("UK", "GBR")]
country_objs = []
for name, iso in countries:
    c, _ = Country.objects.get_or_create(name=name, iso_code=iso)
    country_objs.append(c)

# -------------------------------
# Crear idiomas
# -------------------------------
languages = [("English", "EN"), ("Spanish", "ES"), ("French", "FR")]
language_objs = []
for name, iso in languages:
    l, _ = Language.objects.get_or_create(name=name, iso_code=iso)
    language_objs.append(l)

# -------------------------------
# Crear géneros
# -------------------------------
genres = ["Action", "Comedy", "Sci-Fi"]
genre_objs = []
for name in genres:
    g, _ = Genre.objects.get_or_create(name=name)
    genre_objs.append(g)

# -------------------------------
# Crear ratings
# -------------------------------
ratings = [("G", 0), ("PG-13", 13), ("R", 18)]
rating_objs = []
for desc, age in ratings:
    r, _ = AgeRating.objects.get_or_create(description=desc, minimum_age=age)
    rating_objs.append(r)

# -------------------------------
# Crear directores
# -------------------------------
directors = ["Steven Spielberg", "Christopher Nolan", "Denis Villeneuve"]
director_objs = []
for i, name in enumerate(directors):
    d, _ = Director.objects.get_or_create(
        name=name,
        birth_date=datetime(1970+i, 1, 1).date(),
        country=random.choice(country_objs)
    )
    director_objs.append(d)

# -------------------------------
# Crear películas
# -------------------------------
for i in range(5):
    movie, _ = Movie.objects.get_or_create(
        title=f"Movie {i+1}",
        year=2000 + i,
        genre=random.choice(genre_objs),
        director=random.choice(director_objs),
        country=random.choice(country_objs),
        language=random.choice(language_objs),
        age_rating=random.choice(rating_objs),
        rating=round(random.uniform(5, 9), 1),
        expires_at=datetime.now() + timedelta(days=365)
    )
    # Asignar todas las plataformas
    movie.platforms.set(platform_objs)

# -------------------------------
# Crear series
# -------------------------------
for i in range(3):
    series, _ = Series.objects.get_or_create(
        title=f"Series {i+1}",
        start_year=2010 + i,
        end_year=2015 + i,
        total_seasons=random.randint(1,5),
        genre=random.choice(genre_objs),
        director=random.choice(director_objs),
        country=random.choice(country_objs),
        language=random.choice(language_objs),
        age_rating=random.choice(rating_objs),
        rating=round(random.uniform(5, 9), 1),
        expires_at=datetime.now() + timedelta(days=365)
    )
    series.platforms.set(platform_objs)

print("Base de datos poblada con datos de prueba ✅")