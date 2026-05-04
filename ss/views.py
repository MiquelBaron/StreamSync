import json

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views import View
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView, UpdateView

from .forms import *
from .models import *
from .roles import (
    ROLE_CONTENT_CONSUMER,
    ROLE_PLATFORM_MANAGER,
    ensure_role_groups,
    get_role_group,
    user_has_role,
)
from .search import DatabaseContentSearchService, SearchCriteria
from .services.platform_analytics import (
    build_platform_report_data,
    genre_clicks_chart_png_base64,
    get_platform_for_platform_manager,
)
from .services.platform_pdf import render_html_to_pdf_bytes
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
class DashboardView(LoginRequiredMixin, TemplateView):
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
            .filter(rating__isnull=False)
            .order_by("-rating")[:10]
        )

        featured_series = (
            Serie.objects
            .select_related("director", "genre", "age_rating", "country", "language")
            .prefetch_related("platforms")
            .filter(rating__isnull=False)
            .order_by("-rating")[:10]
        )

        context["has_searched"] = has_searched
        context["search_form"] = form
        context["results"] = results
        context["featured_movies"] = featured_movies
        context["featured_series"] = featured_series
        context["director_suggestions"] = Director.objects.order_by("name").values_list("name", flat=True)

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


class PlatformAnalyticsPdfView(LoginRequiredMixin, UserPassesTestMixin, View):
    login_url = "/login/"
    raise_exception = True

    def test_func(self):
        return user_has_role(self.request.user, ROLE_PLATFORM_MANAGER) and hasattr(
            self.request.user, "plataformmanager"
        )

    def get(self, request, *args, **kwargs):
        platform = get_platform_for_platform_manager(request.user)
        report = build_platform_report_data(platform)
        chart_b64 = genre_clicks_chart_png_base64(report.clicks_per_genre)
        html = render_to_string(
            "reports/platform_analytics_pdf.html",
            {"report": report, "chart_b64": chart_b64},
            request=request,
        )
        pdf_bytes = render_html_to_pdf_bytes(html)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="informe-plataforma.pdf"'
        return response



