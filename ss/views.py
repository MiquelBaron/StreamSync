import csv
import json

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views import View
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView, UpdateView
from itertools import chain

from .forms import *
from .models import *
from .roles import (
    ROLE_CONTENT_CONSUMER,
    ROLE_GENERAL_DIRECTOR,
    ROLE_PLATFORM_MANAGER,
    ensure_role_groups,
    get_role_group,
    user_has_role,
)
from .search import DatabaseContentSearchService, SearchCriteria
from .services.platform_analytics import (
    build_platform_dashboard_data,
    content_type_chart_png_base64,
    genre_clicks_chart_png_base64,
    get_platform_for_platform_manager,
    top_genres_chart_png_base64,
)
from .services.director_dashboard_services import DirectorDashboardService
from .services.platform_manager_dashboard_service import PlatformManagerDashboardService
from .services.visualizations import register_visualization


class CustomLoginView(LoginView):
    template_name = "login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        return "/dashboard/"


class CustomLogoutView(LogoutView):
    next_page = "/login/"


class RegisterView(CreateView):
    template_name = "register.html"
    form_class = UserCreationForm
    success_url = reverse_lazy("login")

    def form_valid(self, form):
        response = super().form_valid(form)
        ensure_role_groups()
        creator_group = get_role_group(ROLE_CONTENT_CONSUMER)
        self.object.groups.add(creator_group)
        return response


@method_decorator(ensure_csrf_cookie, name="dispatch")
class DashboardView(TemplateView):
    template_name = "dashboard.html"
    login_url = "/login/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        form = ContentSearchForm(self.request.GET or None)
        results = []

        has_searched = bool(self.request.GET)

        if has_searched and form.is_valid():
            criteria = SearchCriteria(
                title=form.cleaned_data["title"],
                director_query=form.cleaned_data["director"],
                genre_id=form.cleaned_data["genre"].id if form.cleaned_data["genre"] else None,
                min_age=form.cleaned_data["age_rating"],
            )
            results = DatabaseContentSearchService().search(criteria)

        featured_movies = (
            Film.objects
            .select_related("director", "genre", "age_rating", "country", "language")
            .prefetch_related("platforms")
            .filter(is_active=True, rating__isnull=False)
            .order_by("-rating")[:10]
        )

        featured_series = (
            Serie.objects
            .select_related("director", "genre", "age_rating", "country", "language")
            .prefetch_related("platforms")
            .filter(is_active=True, rating__isnull=False)
            .order_by("-rating")[:10]
        )
        preferred_content = []
        is_content_consumer = (
            self.request.user.is_authenticated
            and user_has_role(self.request.user, ROLE_CONTENT_CONSUMER)
            and hasattr(self.request.user, "contentconsumer")
        )

        if is_content_consumer:
            profile = self.request.user.contentconsumer
            preferred_genres = profile.preferred_genres.all()

            if preferred_genres.exists():
                preferred_movies = (
                    Film.objects.select_related(
                        "director", "genre", "age_rating", "country", "language"
                    )
                    .prefetch_related("platforms")
                    .filter(is_active=True, genre__in=preferred_genres)
                    .order_by("title")[:6]
                )

                preferred_series = (
                    Serie.objects.select_related(
                        "director", "genre", "age_rating", "country", "language"
                    )
                    .prefetch_related("platforms")
                    .filter(is_active=True, genre__in=preferred_genres)
                    .order_by("title")[:6]
                )

                preferred_content = sorted(
                    chain(preferred_movies, preferred_series),
                    key=lambda item: item.title.lower(),
                )[:10]

        context["has_searched"] = has_searched
        context["search_form"] = form
        context["results"] = results
        context["featured_movies"] = featured_movies
        context["featured_series"] = featured_series
        context["director_suggestions"] = Director.objects.order_by("name").values_list("name", flat=True)

        context["is_content_consumer"] = is_content_consumer
        context["preferred_content"] = preferred_content

        return context


class PreferencesView(LoginRequiredMixin, UpdateView):
    model = ContentConsumer
    form_class = PreferencesForm
    template_name = "preferences.html"
    success_url = reverse_lazy("dashboard")

    def get_object(self, queryset=None):
        return self.request.user.contentconsumer


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "profile_page.html"
    login_url = "/login/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.groups.exists():
            profile_role = user.groups.first().name
        elif user.is_superuser or user.is_staff:
            profile_role = "Administrador"
        elif user_has_role(user, ROLE_CONTENT_CONSUMER) and hasattr(user, "contentconsumer"):
            profile_role = "Consumidor de contingut"
        else:
            profile_role = "Usuari"

        context["profile_role"] = profile_role
        if user_has_role(user, ROLE_CONTENT_CONSUMER):
            context["favorite_content"] = user.contentconsumer.preferred_genres.all()
        return context


def home_redirect(request):
    return redirect("/dashboard/")


class RegisterVisualizationView(LoginRequiredMixin, View):
    login_url = "/login/"

    def post(self, request, *args, **kwargs):
        try:
            body = json.loads(request.body.decode())
            content_id = int(body["content_id"])
            platform_id = int(body["platform_id"])
        except (ValueError, KeyError, json.JSONDecodeError, TypeError):
            return JsonResponse({"ok": False, "error": "Dades invàlides."}, status=400)
        try:
            register_visualization(request.user, content_id, platform_id)
        except Content.DoesNotExist:
            return JsonResponse({"ok": False, "error": "Contingut no trobat."}, status=404)
        except ValueError as e:
            return JsonResponse({"ok": False, "error": str(e)}, status=400)
        return JsonResponse({"ok": True})


class PlatformAnalyticsDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "analytics_dashboard/platform_manager_dashboard.html"
    login_url = "/login/"
    raise_exception = True

    def test_func(self):
        return user_has_role(self.request.user, ROLE_PLATFORM_MANAGER) and hasattr(
            self.request.user, "plataformmanager"
        )

    def _get_filtered_dashboard(self):
        platform = get_platform_for_platform_manager(self.request.user)
        data = self.request.GET.copy()
        if "platform" not in data:
            data["platform"] = str(platform.pk)
        form = PlatformAnalyticsFilterForm(data or None, platform=platform)

        period = ""
        content_type = ""
        if form.is_valid():
            period = form.cleaned_data.get("period") or ""
            content_type = form.cleaned_data.get("content_type") or ""

        dashboard = build_platform_dashboard_data(
            platform,
            period=period,
            content_type=content_type,
        )
        return form, dashboard

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form, dashboard = self._get_filtered_dashboard()
        service = PlatformManagerDashboardService(
            platform=get_platform_for_platform_manager(self.request.user),
            filters={
                "period": form.cleaned_data.get("period") if form.is_valid() else "",
                "content_type": form.cleaned_data.get("content_type") if form.is_valid() else "",
            },
        )
        context.update(service.get_dashboard_context())
        context["filter_form"] = form
        context["dashboard"] = dashboard
        context["export_querystring"] = self.request.GET.urlencode()
        context["chart_data"] = {
            "genreViews": [
                {
                    "label": row["genre__name"] or "Sense genere",
                    "value": row["clicks"],
                }
                for row in dashboard.clicks_per_genre
            ],
            "contentTypeViews": [
                {"label": row["label"], "value": row["clicks"]}
                for row in dashboard.content_type_clicks
            ],
            "topGenres": [
                {
                    "label": row["genre__name"] or "Sense genere",
                    "value": row["clicks"],
                }
                for row in dashboard.top_genres
            ],
        }
        return context


class PlatformAnalyticsPdfView(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = "/login/"
    raise_exception = True

    def test_func(self):
        return user_has_role(self.request.user, ROLE_PLATFORM_MANAGER) and hasattr(
            self.request.user, "plataformmanager"
        )

    def get(self, request, *args, **kwargs):
        from .services.platform_pdf import render_html_to_pdf_bytes

        platform = get_platform_for_platform_manager(request.user)
        data = request.GET.copy()
        if "platform" not in data:
            data["platform"] = str(platform.pk)
        form = PlatformAnalyticsFilterForm(data or None, platform=platform)

        period = ""
        content_type = ""
        if form.is_valid():
            period = form.cleaned_data.get("period") or ""
            content_type = form.cleaned_data.get("content_type") or ""

        dashboard = build_platform_dashboard_data(
            platform,
            period=period,
            content_type=content_type,
        )
        html = render_to_string(
            "reports/platform_analytics_pdf.html",
            {
                "dashboard": dashboard,
                "filter_form": form,
                "genre_chart_b64": genre_clicks_chart_png_base64(dashboard.clicks_per_genre),
                "content_type_chart_b64": content_type_chart_png_base64(dashboard.content_type_clicks),
                "top_genres_chart_b64": top_genres_chart_png_base64(dashboard.top_genres),
            },
            request=request,
        )
        pdf_bytes = render_html_to_pdf_bytes(html)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="informe-plataforma.pdf"'
        return response


class PlatformAnalyticsCsvView(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = "/login/"
    raise_exception = True

    def test_func(self):
        return user_has_role(self.request.user, ROLE_PLATFORM_MANAGER) and hasattr(
            self.request.user, "plataformmanager"
        )

    def get(self, request, *args, **kwargs):
        platform = get_platform_for_platform_manager(request.user)
        data = request.GET.copy()
        if "platform" not in data:
            data["platform"] = str(platform.pk)
        form = PlatformAnalyticsFilterForm(data or None, platform=platform)

        period = ""
        if form.is_valid():
            period = form.cleaned_data.get("period") or ""

        dashboard = build_platform_dashboard_data(platform, period=period)

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="analitica-plataforma.csv"'
        response.write("\ufeff")
        writer = csv.writer(response)
        writer.writerow(["seccio", "element", "posicio", "visualitzacions", "valor"])
        writer.writerow(["KPI", "Pellicules totals", "", "", dashboard.catalog_kpis.film_count])
        writer.writerow(["KPI", "Series totals", "", "", dashboard.catalog_kpis.serie_count])
        writer.writerow(["KPI", "Visualitzacions series", "", "", dashboard.report_kpis.serie_visualizations])
        writer.writerow(["KPI", "Visualitzacions pellicules", "", "", dashboard.report_kpis.film_visualizations])

        for index, row in enumerate(dashboard.top_films, start=1):
            writer.writerow(["Top 3 pellicules", row["content__title"], index, row["clicks"], ""])

        for index, row in enumerate(dashboard.top_series, start=1):
            writer.writerow(["Top 3 series", row["content__title"], index, row["clicks"], ""])

        return response


class DirectorDashboardView(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = "/login/"
    raise_exception = True

    def test_func(self):
        return user_has_role(self.request.user, ROLE_GENERAL_DIRECTOR)

    def get(self, request, *args, **kwargs):
        service = DirectorDashboardService(filters=self._parse_filters(request.GET))
        return render(
            request,
            "analytics_dashboard/director_dashboard.html",
            service.get_dashboard_context(),
        )

    @staticmethod
    def _parse_filters(get_params) -> dict:
        filters = {}

        period = get_params.get("period")
        if period in ("day", "week", "month"):
            filters["period"] = period

        content_type = get_params.get("content_type")
        if content_type in ("film", "serie"):
            filters["content_type"] = content_type

        platform_id = get_params.get("platform_id")
        if platform_id and platform_id.isdigit():
            filters["platform_id"] = int(platform_id)

        return filters

