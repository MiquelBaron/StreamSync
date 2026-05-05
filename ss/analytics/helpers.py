from django.core.exceptions import PermissionDenied
from django.db.models import Case, CharField, Count, Value, When

from ss.models import Visualization


def get_platform_for_platform_manager(user):
    if not hasattr(user, "plataformmanager"):
        raise PermissionDenied("Només els gestors de plataforma poden accedir a aquest informe.")
    return user.plataformmanager.platform


def base_platform_visualizations_queryset(platform):
    return Visualization.objects.filter(platform=platform, content__is_active=True)


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

