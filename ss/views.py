from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView, UpdateView

from .forms import *
from .models import *
from .search import DatabaseContentSearchService, SearchCriteria


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
        creator_group = Group.objects.get(name="Consumidor de contingut")
        self.object.groups.add(creator_group)
        return response


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
            Movie.objects.select_related("director", "genre", "age_rating", "country", "language")
            .prefetch_related("platforms")
            .order_by("title")[:6]
        )

        featured_series = (
            Series.objects.select_related("director", "genre", "age_rating", "country", "language")
            .prefetch_related("platforms")
            .order_by("title")[:6]
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
        return self.request.user.content_consumer_profile


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
        elif hasattr(user, "content_consumer_profile"):
            profile_role = "Consumidor de contingut"
        else:
            profile_role = "Usuari"

        context["profile_role"] = profile_role
        if user.groups.exists() and user.groups.first().name == "Consumidor de contingut":
            context["favorite_content"] = user.content_consumer_profile.preferred_genres.all()
        return context


def home_redirect(request):
    return redirect("/dashboard/")



