from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from .forms import ContentSearchForm
from .models import (
    AgeRating,
    ContentConsumer,
    Country,
    Director,
    Film,
    Genre,
    Incidence,
    Language,
    PlataformManager,
    Platform,
    Serie,
    Visualization,
)
from .roles import (
    ROLE_CONTENT_CONSUMER,
    ROLE_PLATFORM_MANAGER,
    ROLE_TECHNICAL_ADMIN,
    ensure_role_groups,
    get_role_group,
)
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

    def test_authenticated_user_can_report_incidence(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("report_incidence"),
            {
                "name": "Error al cercador",
                "description": "La cerca no retorna els resultats esperats.",
            },
            HTTP_REFERER=reverse("dashboard"),
        )

        self.assertRedirects(response, reverse("dashboard"))
        incidence = Incidence.objects.get(name="Error al cercador")
        self.assertEqual(incidence.user, self.user)
        self.assertEqual(incidence.description, "La cerca no retorna els resultats esperats.")


class UserManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_role_groups()
        User = get_user_model()
        cls.technical_admin = User.objects.create_user(
            username="admin_tecnic",
            password="secret123",
            email="admin@example.com",
        )
        cls.technical_admin.groups.add(get_role_group(ROLE_TECHNICAL_ADMIN))

        cls.regular_user = User.objects.create_user(
            username="usuari",
            password="secret123",
            email="usuari@example.com",
        )

        cls.platform_user = User.objects.create_user(
            username="gestor",
            password="secret123",
            email="gestor@example.com",
        )
        cls.platform_user.groups.add(get_role_group(ROLE_PLATFORM_MANAGER))

    def test_technical_admin_sees_user_management_link_in_navbar(self):
        self.client.force_login(self.technical_admin)

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Gestionar usuaris")

    def test_technical_admin_can_access_user_management(self):
        self.client.force_login(self.technical_admin)

        response = self.client.get(reverse("user_management"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Gestio d'usuaris")
        self.assertContains(response, "admin_tecnic")
        self.assertContains(response, "usuari")

    def test_non_technical_admin_cannot_access_user_management(self):
        self.client.force_login(self.regular_user)

        response = self.client.get(reverse("user_management"))

        self.assertEqual(response.status_code, 403)

    def test_user_management_filters_by_role(self):
        self.client.force_login(self.technical_admin)
        role = get_role_group(ROLE_PLATFORM_MANAGER)

        response = self.client.get(reverse("user_management"), {"role": role.pk})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "gestor")
        self.assertNotContains(response, "usuari@example.com")

    def test_technical_admin_can_create_user(self):
        self.client.force_login(self.technical_admin)
        role = get_role_group(ROLE_PLATFORM_MANAGER)

        response = self.client.post(
            reverse("user_management"),
            {
                "username": "nou_usuari",
                "first_name": "Nou",
                "last_name": "Usuari",
                "email": "nou@example.com",
                "password": "secret123",
                "role": role.pk,
            },
        )

        self.assertRedirects(response, reverse("user_management"))
        user = get_user_model().objects.get(username="nou_usuari")
        self.assertTrue(user.check_password("secret123"))
        self.assertEqual(user.email, "nou@example.com")
        self.assertTrue(user.groups.filter(pk=role.pk).exists())

    def test_technical_admin_can_update_existing_user_role(self):
        self.client.force_login(self.technical_admin)
        role = get_role_group(ROLE_TECHNICAL_ADMIN)

        response = self.client.post(
            reverse("user_management"),
            {
                "action": "update_role",
                "user_id": self.regular_user.pk,
                "role": role.pk,
            },
        )

        self.assertRedirects(response, reverse("user_management"))
        self.assertTrue(self.regular_user.groups.filter(pk=role.pk).exists())

    def test_technical_admin_can_update_existing_user_to_consumer_role(self):
        self.client.force_login(self.technical_admin)
        role = get_role_group(ROLE_CONTENT_CONSUMER)

        response = self.client.post(
            reverse("user_management"),
            {
                "action": "update_role",
                "user_id": self.regular_user.pk,
                "role": role.pk,
            },
        )

        self.assertRedirects(response, reverse("user_management"))
        self.assertTrue(get_user_model().objects.filter(pk=self.regular_user.pk).exists())
        self.assertTrue(ContentConsumer.objects.filter(pk=self.regular_user.pk).exists())
        self.assertTrue(self.regular_user.groups.filter(pk=role.pk).exists())

    def test_technical_admin_can_update_consumer_to_other_role_without_deleting_user(self):
        consumer_role = get_role_group(ROLE_CONTENT_CONSUMER)
        self.regular_user.groups.add(consumer_role)
        self.assertTrue(ContentConsumer.objects.filter(pk=self.regular_user.pk).exists())

        self.client.force_login(self.technical_admin)
        technical_role = get_role_group(ROLE_TECHNICAL_ADMIN)

        response = self.client.post(
            reverse("user_management"),
            {
                "action": "update_role",
                "user_id": self.regular_user.pk,
                "role": technical_role.pk,
            },
        )

        self.assertRedirects(response, reverse("user_management"))
        self.assertTrue(get_user_model().objects.filter(pk=self.regular_user.pk).exists())
        self.assertFalse(ContentConsumer.objects.filter(pk=self.regular_user.pk).exists())
        self.assertTrue(self.regular_user.groups.filter(pk=technical_role.pk).exists())

    def test_updating_one_consumer_role_does_not_change_other_consumers(self):
        User = get_user_model()
        consumer_role = get_role_group(ROLE_CONTENT_CONSUMER)
        other_consumer = User.objects.create_user(
            username="altre_consumidor",
            password="secret123",
            email="altre@example.com",
        )
        self.regular_user.groups.add(consumer_role)
        other_consumer.groups.add(consumer_role)

        self.client.force_login(self.technical_admin)
        technical_role = get_role_group(ROLE_TECHNICAL_ADMIN)

        response = self.client.post(
            reverse("user_management"),
            {
                "action": "update_role",
                "user_id": self.regular_user.pk,
                "role": technical_role.pk,
            },
        )

        self.assertRedirects(response, reverse("user_management"))
        self.assertTrue(self.regular_user.groups.filter(pk=technical_role.pk).exists())
        self.assertFalse(self.regular_user.groups.filter(pk=consumer_role.pk).exists())
        self.assertTrue(other_consumer.groups.filter(pk=consumer_role.pk).exists())
        self.assertFalse(other_consumer.groups.filter(pk=technical_role.pk).exists())

    def test_technical_admin_can_delete_user_with_confirmation_post(self):
        self.client.force_login(self.technical_admin)

        response = self.client.post(
            reverse("user_management"),
            {
                "action": "delete",
                "user_id": self.regular_user.pk,
            },
        )

        self.assertRedirects(response, reverse("user_management"))
        self.assertFalse(get_user_model().objects.filter(pk=self.regular_user.pk).exists())

    def test_technical_admin_cannot_delete_self(self):
        self.client.force_login(self.technical_admin)

        response = self.client.post(
            reverse("user_management"),
            {
                "action": "delete",
                "user_id": self.technical_admin.pk,
            },
        )

        self.assertRedirects(response, reverse("user_management"))
        self.assertTrue(get_user_model().objects.filter(pk=self.technical_admin.pk).exists())


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
