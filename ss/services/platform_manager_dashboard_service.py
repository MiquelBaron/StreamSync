from ss.models import Film, Platform, Serie

from .director_dashboard_services import DirectorDashboardService


class PlatformManagerDashboardService(DirectorDashboardService):
    def __init__(self, platform: Platform, filters: dict | None = None):
        self.platform = platform
        forced_filters = dict(filters or {})
        forced_filters["platform_id"] = platform.id
        super().__init__(forced_filters)

    def get_dashboard_context(self) -> dict:
        context = super().get_dashboard_context()
        context["filter_options"] = {
            "platforms": [{"id": self.platform.id, "name": self.platform.name}],
        }
        return context

    def _get_kpis(self) -> dict:
        film_count = (
            Film.objects.filter(platforms=self.platform, is_active=True).distinct().count()
        )
        serie_count = (
            Serie.objects.filter(platforms=self.platform, is_active=True).distinct().count()
        )
        film_views = self._visualizations_qs.filter(content__film__isnull=False).count()
        serie_views = self._visualizations_qs.filter(content__serie__isnull=False).count()
        return {
            "total_films": film_count,
            "total_series": serie_count,
            "total_content": film_count + serie_count,
            "total_visualizations": self._visualizations_qs.count(),
            "film_visualizations": film_views,
            "serie_visualizations": serie_views,
        }

    def _get_films_list(self) -> list:
        return list(
            Film.objects.filter(platforms=self.platform, is_active=True)
            .distinct()
            .select_related("genre", "director")
            .values("id", "title", "year", "genre__name", "director__name", "rating")
        )

    def _get_series_list(self) -> list:
        return list(
            Serie.objects.filter(platforms=self.platform, is_active=True)
            .distinct()
            .select_related("genre", "director")
            .values(
                "id",
                "title",
                "start_year",
                "end_year",
                "total_seasons",
                "genre__name",
                "director__name",
                "rating",
            )
        )
