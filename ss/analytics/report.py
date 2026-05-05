import base64
import io
from dataclasses import dataclass

import matplotlib

from .helpers import (
    aggregate_clicks_per_genre,
    aggregate_content_clicks_table,
    base_platform_visualizations_queryset,
    compute_platform_report_kpis,
)

matplotlib.use("Agg")
import matplotlib.pyplot as plt


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
    base = base_platform_visualizations_queryset(platform)
    kpis = compute_platform_report_kpis(base)
    clicks_per_genre = aggregate_clicks_per_genre(base)
    content_table = aggregate_content_clicks_table(base)
    return PlatformReportData(
        platform_name=platform.name,
        kpis=PlatformReportKpis(**kpis),
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

