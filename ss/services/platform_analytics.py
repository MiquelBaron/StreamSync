import base64
import io
from dataclasses import dataclass

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from django.core.exceptions import PermissionDenied
from django.db.models import Case, CharField, Count, Value, When

from ss.models import Visualization


def get_platform_for_platform_manager(user):
    if not hasattr(user, "plataformmanager"):
        raise PermissionDenied("Només els gestors de plataforma poden accedir a aquest informe.")
    return user.plataformmanager.platform


@dataclass(frozen=True)
class PlatformReportKpis:
    total_visualizations: int
    film_visualizations: int
    serie_visualizations: int


@dataclass(frozen=True)
class PlatformReportData:
    platform_name: str
    kpis: PlatformReportKpis
    clicks_per_genre: list[dict]
    content_table: list[dict]


def build_platform_report_data(platform) -> PlatformReportData:
    base = Visualization.objects.filter(platform=platform, content__is_active=True)
    total = base.count()
    film_visualizations = base.filter(content__film__isnull=False).count()
    serie_visualizations = base.filter(content__serie__isnull=False).count()

    clicks_per_genre = list(
        base.values("genre__name")
        .annotate(clicks=Count("id"))
        .order_by("-clicks", "genre__name")
    )

    content_table = list(
        base.values("content_id", "content__title")
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

    return PlatformReportData(
        platform_name=platform.name,
        kpis=PlatformReportKpis(
            total_visualizations=total,
            film_visualizations=film_visualizations,
            serie_visualizations=serie_visualizations,
        ),
        clicks_per_genre=clicks_per_genre,
        content_table=content_table,
    )


def genre_clicks_chart_png_base64(clicks_per_genre: list[dict]) -> str:
    """Bar chart of genre names vs clicks; returns raw base64 (no data: prefix)."""
    if not clicks_per_genre:
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.text(0.5, 0.5, "Sense dades", ha="center", va="center")
        ax.axis("off")
    else:
        labels = [row["genre__name"] or "—" for row in clicks_per_genre]
        values = [row["clicks"] for row in clicks_per_genre]
        fig, ax = plt.subplots(figsize=(max(6, len(labels) * 0.5), 3.5))
        ax.bar(labels, values, color="#e50914")
        ax.set_ylabel("Clicks")
        ax.tick_params(axis="x", rotation=35, labelsize=8)
        fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")
