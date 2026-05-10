from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from .forms import ContentSearchForm
from .models import (
    AgeRating,
    Country,
    Director,
    Film,
    Genre,
    Language,
    PlataformManager,
    Platform,
    Serie,
    Visualization,
)
from .roles import ROLE_PLATFORM_MANAGER, ensure_role_groups, get_role_group
from .search import DatabaseContentSearchService, SearchCriteria


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

        dune = Film.objects.create(
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

        duel = Film.objects.create(
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

        mystery_series = Serie.objects.create(
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

    def test_profile_page_renders_user_information(self):
        self.user.email = "tester@example.com"
        self.user.save()
        self.client.force_login(self.user)

        response = self.client.get(reverse("profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "tester")
        self.assertContains(response, "tester@example.com")
        self.assertContains(response, "Contingut marcat com a preferit")

    def test_profile_page_shows_admin_role_for_superuser_without_groups(self):
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()
        self.client.force_login(self.user)

        response = self.client.get(reverse("profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Administrador")


class PlatformAnalyticsDashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_role_groups()
        country = Country.objects.create(name="Espanya", iso_code="ESP")
        language = Language.objects.create(name="Catala", iso_code="CAT")
        age_13 = AgeRating.objects.create(description="13+", minimum_age=13)
        director = Director.objects.create(name="Directora", country=country)
        cls.scifi = Genre.objects.create(name="Ciencia ficcio")
        cls.horror = Genre.objects.create(name="Terror")
        cls.netflix = Platform.objects.create(name="Netflix")
        cls.hbo = Platform.objects.create(name="HBO Max")

        cls.netflix_film = Film.objects.create(
            title="Film Netflix",
            synopsis="",
            year=2024,
            genre=cls.scifi,
            director=director,
            country=country,
            language=language,
            age_rating=age_13,
        )
        cls.netflix_film.platforms.add(cls.netflix)

        cls.netflix_serie = Serie.objects.create(
            title="Serie Netflix",
            synopsis="",
            start_year=2024,
            total_seasons=1,
            genre=cls.scifi,
            director=director,
            country=country,
            language=language,
            age_rating=age_13,
        )
        cls.netflix_serie.platforms.add(cls.netflix)

        cls.hbo_film = Film.objects.create(
            title="Film HBO",
            synopsis="",
            year=2024,
            genre=cls.horror,
            director=director,
            country=country,
            language=language,
            age_rating=age_13,
        )
        cls.hbo_film.platforms.add(cls.hbo)

        cls.manager = PlataformManager.objects.create_user(
            username="gestor_netflix",
            password="secret123",
            platform=cls.netflix,
        )
        cls.manager.groups.add(get_role_group(ROLE_PLATFORM_MANAGER))
        cls.other_user = get_user_model().objects.create_user(
            username="plain",
            password="secret123",
        )

        base = timezone.now()
        Visualization.objects.create(
            user=cls.other_user,
            viewed_at=base - timedelta(days=1),
            content=cls.netflix_film,
            genre=cls.scifi,
            platform=cls.netflix,
        )
        Visualization.objects.create(
            user=cls.manager,
            viewed_at=base - timedelta(days=2),
            content=cls.netflix_serie,
            genre=cls.scifi,
            platform=cls.netflix,
        )
        Visualization.objects.create(
            user=cls.other_user,
            viewed_at=base - timedelta(days=20),
            content=cls.netflix_film,
            genre=cls.scifi,
            platform=cls.netflix,
        )
        Visualization.objects.create(
            user=cls.manager,
            viewed_at=base - timedelta(days=1),
            content=cls.hbo_film,
            genre=cls.horror,
            platform=cls.hbo,
        )

    def test_platform_manager_can_access_own_dashboard(self):
        self.client.force_login(self.manager)

        response = self.client.get(reverse("platform_analytics_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["dashboard"].platform_name, "Netflix")
        self.assertEqual(response.context["dashboard"].catalog_kpis.film_count, 1)
        self.assertEqual(response.context["dashboard"].catalog_kpis.serie_count, 1)
        self.assertEqual(response.context["dashboard"].report_kpis.total_visualizations, 3)

    def test_non_platform_manager_cannot_access_dashboard(self):
        self.client.force_login(self.other_user)

        response = self.client.get(reverse("platform_analytics_dashboard"))

        self.assertEqual(response.status_code, 403)

    def test_tampered_platform_filter_still_uses_managed_platform(self):
        self.client.force_login(self.manager)

        response = self.client.get(
            reverse("platform_analytics_dashboard"),
            {"platform": self.hbo.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["dashboard"].platform_name, "Netflix")
        labels = [row["label"] for row in response.context["chart_data"]["genreViews"]]
        self.assertEqual(labels, ["Ciencia ficcio"])

    def test_filters_apply_to_managed_platform_data(self):
        self.client.force_login(self.manager)

        response = self.client.get(
            reverse("platform_analytics_dashboard"),
            {
                "platform": self.netflix.pk,
                "period": "days",
                "content_type": "film",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["dashboard"].report_kpis.total_visualizations, 1)
        self.assertEqual(response.context["dashboard"].report_kpis.film_visualizations, 1)
        self.assertEqual(response.context["dashboard"].report_kpis.serie_visualizations, 0)

    def test_platform_manager_can_export_csv_with_kpis_and_top_content(self):
        self.client.force_login(self.manager)

        response = self.client.get(reverse("platform_analytics_csv"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        body = response.content.decode("utf-8-sig")
        self.assertIn("KPI,Pellicules totals,,,1", body)
        self.assertIn("KPI,Series totals,,,1", body)
        self.assertIn("KPI,Visualitzacions series,,,1", body)
        self.assertIn("KPI,Visualitzacions pellicules,,,2", body)
        self.assertIn("Top 3 pellicules,Film Netflix,1,2,", body)
        self.assertIn("Top 3 series,Serie Netflix,1,1,", body)

    def test_non_platform_manager_cannot_export_csv(self):
        self.client.force_login(self.other_user)

        response = self.client.get(reverse("platform_analytics_csv"))

        self.assertEqual(response.status_code, 403)

    def test_platform_manager_can_export_pdf(self):
        self.client.force_login(self.manager)

        response = self.client.get(reverse("platform_analytics_pdf"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))
