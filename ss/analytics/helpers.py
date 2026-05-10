from django.core.exceptions import PermissionDenied
from datetime import timedelta

from django.db.models import Case, CharField, Count, Value, When
from django.utils import timezone

from ss.models import Film, Serie, Visualization


def get_platform_for_platform_manager(user):
    if not hasattr(user, "plataformmanager"):
        raise PermissionDenied("Només els gestors de plataforma poden accedir a aquest informe.")
    return user.plataformmanager.platform


def base_platform_visualizations_queryset(platform):
    return Visualization.objects.filter(platform=platform, content__is_active=True)


def filter_visualizations_by_period(base_queryset, period: str | None):
    period_days = {
        "days": 7,
        "weeks": 28,
        "months": 365,
    }
    days = period_days.get(period or "")
    if not days:
        return base_queryset
    return base_queryset.filter(viewed_at__gte=timezone.now() - timedelta(days=days))


def filter_visualizations_by_content_type(base_queryset, content_type: str | None):
    if content_type == "film":
        return base_queryset.filter(content__film__isnull=False)
    if content_type == "serie":
        return base_queryset.filter(content__serie__isnull=False)
    return base_queryset


def compute_platform_catalog_kpis(platform) -> dict[str, int]:
    return {
        "film_count": Film.objects.filter(platforms=platform, is_active=True).distinct().count(),
        "serie_count": Serie.objects.filter(platforms=platform, is_active=True).distinct().count(),
    }


def compute_platform_report_kpis(base_queryset) -> dict[str, int]:
    return {
        "total_visualizations": base_queryset.count(),
        "film_visualizations": base_queryset.filter(content__film__isnull=False).count(),
        "serie_visualizations": base_queryset.filter(content__serie__isnull=False).count(),
    }


def aggregate_clicks_per_genre(base_queryset) -> list[dict]:
    return list(
        base_queryset.values("genre__name")
        .annotate(clicks=Count("id"))
        .order_by("-clicks", "genre__name")
    )


def aggregate_content_clicks_table(base_queryset) -> list[dict]:
    return list(
        base_queryset.values("content_id", "content__title")
        .annotate(
            clicks=Count("id"),
            tipus=Case(
                When(content__film__isnull=False, then=Value("Pel·lícula")),
                When(content__serie__isnull=False, then=Value("Sèrie")),
                default=Value("—"),
                output_field=CharField(),
            ),
        )
        .order_by("-clicks", "content__title")
    )


def aggregate_top_content_by_type(base_queryset, content_type: str, limit: int = 3) -> list[dict]:
    return aggregate_content_clicks_table(
        filter_visualizations_by_content_type(base_queryset, content_type)
    )[:limit]

