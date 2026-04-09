from django.core.management.base import BaseCommand
from ss.models import Country, Platform, Genre, Director, AgeRating, Language, Movie, Series
from datetime import date, timedelta
from django.utils import timezone

class Command(BaseCommand):
    help = "Populate database with demo data for StreamSync"

    def handle(self, *args, **options):
        # --- Countries ---
        countries = [
            ("USA", "USA"),
            ("Canada", "CAN"),
            ("UK", "GBR"),
        ]
        for name, iso in countries:
            obj, created = Country.objects.get_or_create(name=name, iso_code=iso)
            self.stdout.write(self.style.SUCCESS(f"Country '{name}' ready"))

        # --- Platforms ---
        platforms = ["Netflix", "HBO Max", "Disney+"]
        for p in platforms:
            obj, created = Platform.objects.get_or_create(name=p)
            self.stdout.write(self.style.SUCCESS(f"Platform '{p}' ready"))

        # --- Genres ---
        genres = [
            ("Sci-Fi", "Science Fiction"),
            ("Drama", "Drama movies and series"),
            ("Comedy", "Comedic content"),
        ]
        for name, desc in genres:
            obj, created = Genre.objects.get_or_create(name=name, description=desc)
            self.stdout.write(self.style.SUCCESS(f"Genre '{name}' ready"))

        # --- Languages ---
        languages = [
            ("English", "EN"),
            ("Spanish", "ES"),
            ("French", "FR"),
        ]
        for name, iso in languages:
            obj, created = Language.objects.get_or_create(name=name, iso_code=iso)
            self.stdout.write(self.style.SUCCESS(f"Language '{name}' ready"))

        # --- Age Ratings ---
        ratings = [
            ("G", 0),
            ("PG-13", 13),
            ("R", 17),
        ]
        for desc, min_age in ratings:
            obj, created = AgeRating.objects.get_or_create(description=desc, minimum_age=min_age)
            self.stdout.write(self.style.SUCCESS(f"AgeRating '{desc}' ready"))

        # --- Directors ---
        directors = [
            ("Christopher Nolan", date(1970, 7, 30), "USA"),
            ("Denis Villeneuve", date(1967, 10, 3), "CAN"),
            ("Danny Boyle", date(1956, 10, 20), "GBR"),
        ]
        for name, bdate, country_iso in directors:
            country = Country.objects.get(iso_code=country_iso)
            obj, created = Director.objects.get_or_create(name=name, birth_date=bdate, country=country)
            self.stdout.write(self.style.SUCCESS(f"Director '{name}' ready"))

        # --- Movies ---
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
            movie_obj, created = Movie.objects.get_or_create(
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
                }
            )
            # Añadir a todas las plataformas demo
            movie_obj.platforms.set(Platform.objects.all())
            movie_obj.save()
            self.stdout.write(self.style.SUCCESS(f"Movie '{m['title']}' ready"))

        # --- Series ---
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
            series_obj, created = Series.objects.get_or_create(
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
                }
            )
            series_obj.platforms.set(Platform.objects.all())
            series_obj.save()
            self.stdout.write(self.style.SUCCESS(f"Series '{s['title']}' ready"))

        self.stdout.write(self.style.SUCCESS("Demo data populated successfully!"))