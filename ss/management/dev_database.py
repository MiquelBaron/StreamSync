"""
Pasos reutilizables para preparar la base de datos de desarrollo.
Los comandos create_roles, create_admin_user y populate_demo_data delegan aquí.
"""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone

from ss.models import (
    AgeRating,
    Country,
    Director,
    Genre,
    Language,
    Movie,
    Platform,
    Series,
)


def run_create_roles(stdout_write, style):
    roles = [
        "Consumidor de contingut",
    ]
    for role_name in roles:
        _, created = Group.objects.get_or_create(name=role_name)
        if created:
            stdout_write(style.SUCCESS(f"Group '{role_name}' created correctly."))
        else:
            stdout_write(style.WARNING(f"Group '{role_name}' already exists."))


def run_create_admin_user(stdout_write, style):
    User = get_user_model()
    username = "admin"
    password = "admin"
    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username=username, password=password)
        stdout_write(style.SUCCESS(f"Superuser '{username}' created successfully."))
    else:
        stdout_write(style.WARNING(f"Superuser '{username}' already exists."))


CONSUMER_GROUP_NAME = "Consumidor de contingut"


def run_create_consumer_user(stdout_write, style):
    User = get_user_model()
    username = "consumidor"
    password = "consumidor"
    group, _ = Group.objects.get_or_create(name=CONSUMER_GROUP_NAME)
    user, created = User.objects.get_or_create(
        username=username,
        defaults={"is_staff": False, "is_superuser": False},
    )
    if created:
        user.set_password(password)
        user.save()
        stdout_write(style.SUCCESS(f"User '{username}' created (password: {password})."))
    else:
        stdout_write(style.WARNING(f"User '{username}' already exists."))
    if not user.groups.filter(pk=group.pk).exists():
        user.groups.add(group)
        stdout_write(style.SUCCESS(f"Role '{CONSUMER_GROUP_NAME}' assigned to '{username}'."))
    else:
        stdout_write(style.WARNING(f"User '{username}' already has role '{CONSUMER_GROUP_NAME}'."))


def run_populate_demo_data(stdout_write, style):
    countries = [
        ("USA", "USA"),
        ("Canada", "CAN"),
        ("UK", "GBR"),
    ]
    for name, iso in countries:
        Country.objects.get_or_create(name=name, iso_code=iso)
        stdout_write(style.SUCCESS(f"Country '{name}' ready"))

    platforms = ["Netflix", "HBO Max", "Disney+"]
    for p in platforms:
        Platform.objects.get_or_create(name=p)
        stdout_write(style.SUCCESS(f"Platform '{p}' ready"))

    genres = [
        ("Sci-Fi", "Science Fiction"),
        ("Drama", "Drama movies and series"),
        ("Comedy", "Comedic content"),
    ]
    for name, desc in genres:
        Genre.objects.get_or_create(name=name, description=desc)
        stdout_write(style.SUCCESS(f"Genre '{name}' ready"))

    languages = [
        ("English", "EN"),
        ("Spanish", "ES"),
        ("French", "FR"),
    ]
    for name, iso in languages:
        Language.objects.get_or_create(name=name, iso_code=iso)
        stdout_write(style.SUCCESS(f"Language '{name}' ready"))

    ratings = [
        ("G", 0),
        ("PG-13", 13),
        ("R", 17),
    ]
    for desc, min_age in ratings:
        AgeRating.objects.get_or_create(description=desc, minimum_age=min_age)
        stdout_write(style.SUCCESS(f"AgeRating '{desc}' ready"))

    directors = [
        ("Christopher Nolan", date(1970, 7, 30), "USA"),
        ("Denis Villeneuve", date(1967, 10, 3), "CAN"),
        ("Danny Boyle", date(1956, 10, 20), "GBR"),
    ]
    for name, bdate, country_iso in directors:
        country = Country.objects.get(iso_code=country_iso)
        Director.objects.get_or_create(name=name, birth_date=bdate, country=country)
        stdout_write(style.SUCCESS(f"Director '{name}' ready"))

    movie_list = [
        {
            "title": "Inception",
            "year": 2010,
            "director": "Christopher Nolan",
            "country": "USA",
            "genre": "Sci-Fi",
            "rating": 8.8,
            "age_rating": "PG-13",
            "language": "EN",
        },
        {
            "title": "Dune",
            "year": 2021,
            "director": "Denis Villeneuve",
            "country": "CAN",
            "genre": "Sci-Fi",
            "rating": 8.1,
            "age_rating": "PG-13",
            "language": "EN",
        },
    ]
    for m in movie_list:
        movie_obj, _ = Movie.objects.get_or_create(
            title=m["title"],
            defaults={
                "year": m["year"],
                "director": Director.objects.get(name=m["director"]),
                "country": Country.objects.get(iso_code=m["country"]),
                "genre": Genre.objects.get(name=m["genre"]),
                "rating": m["rating"],
                "age_rating": AgeRating.objects.get(description=m["age_rating"]),
                "language": Language.objects.get(iso_code=m["language"]),
                "expires_at": timezone.now() + timedelta(days=365),
            },
        )
        movie_obj.platforms.set(Platform.objects.all())
        movie_obj.save()
        stdout_write(style.SUCCESS(f"Movie '{m['title']}' ready"))

    series_list = [
        {
            "title": "Stranger Things",
            "start_year": 2016,
            "end_year": 2024,
            "total_seasons": 5,
            "director": "Danny Boyle",
            "country": "GBR",
            "genre": "Sci-Fi",
            "rating": 8.7,
            "age_rating": "PG-13",
            "language": "EN",
        }
    ]
    for s in series_list:
        series_obj, _ = Series.objects.get_or_create(
            title=s["title"],
            defaults={
                "start_year": s["start_year"],
                "end_year": s["end_year"],
                "total_seasons": s["total_seasons"],
                "director": Director.objects.get(name=s["director"]),
                "country": Country.objects.get(iso_code=s["country"]),
                "genre": Genre.objects.get(name=s["genre"]),
                "rating": s["rating"],
                "age_rating": AgeRating.objects.get(description=s["age_rating"]),
                "language": Language.objects.get(iso_code=s["language"]),
                "expires_at": timezone.now() + timedelta(days=365),
            },
        )
        series_obj.platforms.set(Platform.objects.all())
        series_obj.save()
        stdout_write(style.SUCCESS(f"Series '{s['title']}' ready"))

    stdout_write(style.SUCCESS("Demo data populated successfully!"))
