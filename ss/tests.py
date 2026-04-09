from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .forms import ContentSearchForm
from .models import AgeRating, Country, Director, Genre, Language, Movie, Platform, Series
from .services.search import DatabaseContentSearchService, SearchCriteria


class SearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        country = Country.objects.create(name="Espanya", iso_code="ESP")
        genre_scifi = Genre.objects.create(name="Ciencia ficcio")
        genre_horror = Genre.objects.create(name="Terror")
        language = Language.objects.create(name="Catala", iso_code="CAT")
        director_nolan = Director.objects.create(name="Christopher Nolan", country=country)
        director_aha = Director.objects.create(name="Ana Hallow", country=country)
        age_13 = AgeRating.objects.create(description="13+", minimum_age=13)
        age_18 = AgeRating.objects.create(description="18+", minimum_age=18)
        netflix = Platform.objects.create(name="Netflix")
        hbo = Platform.objects.create(name="HBO Max")

        dune = Movie.objects.create(
            title="Dune",
            synopsis="Sci-fi epic",
            year=2021,
            genre=genre_scifi,
            director=director_nolan,
            country=country,
            language=language,
            age_rating=age_13,
        )
        dune.platforms.add(netflix)

        duel = Movie.objects.create(
            title="El Duel",
            synopsis="Thriller",
            year=2020,
            genre=genre_horror,
            director=director_aha,
            country=country,
            language=language,
            age_rating=age_18,
        )
        duel.platforms.add(hbo)

        mystery_series = Series.objects.create(
            title="El Laboratori",
            synopsis="Misteri",
            start_year=2023,
            total_seasons=1,
            genre=genre_horror,
            director=director_aha,
            country=country,
            language=language,
            age_rating=age_18,
        )
        mystery_series.platforms.add(netflix, hbo)

        cls.user = get_user_model().objects.create_user(username="tester", password="secret123")

    def test_title_search_is_case_insensitive(self):
        service = DatabaseContentSearchService()
        results = service.search(SearchCriteria(title="eL"))
        self.assertEqual([item["title"] for item in results], ["El Duel", "El Laboratori"])

    def test_director_search_matches_partial_text(self):
        service = DatabaseContentSearchService()
        results = service.search(SearchCriteria(director_query="nol"))
        self.assertEqual([item["title"] for item in results], ["Dune"])

    def test_filters_can_be_combined(self):
        service = DatabaseContentSearchService()
        genre = Genre.objects.get(name="Terror")
        results = service.search(
            SearchCriteria(
                title="el",
                director_query="ana",
                genre_id=genre.id,
                min_age=18,
            )
        )
        self.assertEqual([item["title"] for item in results], ["El Duel", "El Laboratori"])

    def test_search_can_use_filters_without_title(self):
        service = DatabaseContentSearchService()
        genre = Genre.objects.get(name="Terror")
        results = service.search(SearchCriteria(genre_id=genre.id, min_age=18))
        self.assertEqual([item["title"] for item in results], ["El Duel", "El Laboratori"])

    def test_age_rating_uses_gte(self):
        service = DatabaseContentSearchService()
        results = service.search(SearchCriteria(min_age=18))
        self.assertEqual([item["title"] for item in results], ["El Duel", "El Laboratori"])

    def test_default_filters_are_valid(self):
        form = ContentSearchForm(
            data={
                "title": "",
                "director": "",
                "genre": "",
                "age_rating": "0",
            }
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["age_rating"], 0)

    def test_default_filters_return_all_content(self):
        service = DatabaseContentSearchService()
        results = service.search(SearchCriteria(title="", min_age=0))
        self.assertEqual([item["title"] for item in results], ["Dune", "El Duel", "El Laboratori"])

    def test_dashboard_renders_all_content_with_default_filters(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("dashboard"),
            {
                "title": "",
                "director": "",
                "genre": "",
                "age_rating": "0",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dune")
        self.assertContains(response, "El Duel")
        self.assertContains(response, "El Laboratori")

    def test_dashboard_renders_results_for_partial_director_search(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("dashboard"),
            {
                "director": "nol",
                "age_rating": "0",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dune")
        self.assertNotContains(response, "El Duel")
