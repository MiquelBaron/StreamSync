from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView, UpdateView
from itertools import chain

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
            Movie.objects.select_related("director", "genre", "age_rating")
            .prefetch_related("platforms")
            .order_by("title")[:6]
        )

        featured_series = (
            Series.objects.select_related("director", "genre", "age_rating")
            .prefetch_related("platforms")
            .order_by("title")[:6]
        )
        preferred_content = []
        is_content_consumer = self.request.user.groups.filter(
            name="Consumidor de contingut"
        ).exists()

        if is_content_consumer:
            profile, _ = ContentConsumer.objects.get_or_create(user=self.request.user)
            preferred_genres = profile.preferred_genres.all()

            if preferred_genres.exists():
                preferred_movies = (
                    Movie.objects.select_related("director", "genre", "age_rating")
                    .prefetch_related("platforms")
                    .filter(genre__in=preferred_genres)
                    .order_by("title")[:6]
                )

                preferred_series = (
                    Series.objects.select_related("director", "genre", "age_rating")
                    .prefetch_related("platforms")
                    .filter(genre__in=preferred_genres)
                    .order_by("title")[:6]
                )

                preferred_content = sorted(
                    chain(preferred_movies, preferred_series),
                    key=lambda item: item.title
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
        return self.request.user.content_consumer_profile

def home_redirect(request):
    return redirect("/dashboard/")



