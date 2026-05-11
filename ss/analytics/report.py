import base64
import io
from dataclasses import dataclass

import matplotlib

from .helpers import (
    aggregate_clicks_per_genre,
    aggregate_content_clicks_table,
    aggregate_top_content_by_type,
    base_platform_visualizations_queryset,
    compute_platform_catalog_kpis,
    compute_platform_report_kpis,
    filter_visualizations_by_content_type,
    filter_visualizations_by_period,
)

matplotlib.use("Agg")
import matplotlib.pyplot as plt


CHART_COLORS = [
    "#e50914",
    "#f5a623",
    "#4a90d9",
    "#7ed321",
    "#9b59b6",
    "#1abc9c",
    "#e67e22",
    "#b81d24",
]


def _chart_colors(count: int) -> list[str]:
    return [CHART_COLORS[index % len(CHART_COLORS)] for index in range(count)]


@dataclass(frozen=True)
class PlatformReportKpis:
    total_visualizations: int
    film_visualizations: int
    serie_visualizations: int


@dataclass(frozen=True)
class PlatformCatalogKpis:
    film_count: int
    serie_count: int


@dataclass(frozen=True)
class PlatformReportData:
    platform_name: str
    catalog_kpis: PlatformCatalogKpis
    kpis: PlatformReportKpis
    clicks_per_genre: list[dict]
    content_table: list[dict]


@dataclass(frozen=True)
class PlatformDashboardData:
    platform_id: int
    platform_name: str
    catalog_kpis: PlatformCatalogKpis
    report_kpis: PlatformReportKpis
    clicks_per_genre: list[dict]
    content_type_clicks: list[dict]
    top_genres: list[dict]
    content_table: list[dict]
    top_films: list[dict]
    top_series: list[dict]


def build_platform_report_data(platform) -> PlatformReportData:
    base = base_platform_visualizations_queryset(platform)
    kpis = compute_platform_report_kpis(base)
    clicks_per_genre = aggregate_clicks_per_genre(base)
    content_table = aggregate_content_clicks_table(base)
    return PlatformReportData(
        platform_name=platform.name,
        catalog_kpis=PlatformCatalogKpis(**compute_platform_catalog_kpis(platform)),
        kpis=PlatformReportKpis(**kpis),
        clicks_per_genre=clicks_per_genre,
        content_table=content_table,
    )


def build_platform_dashboard_data(
    platform,
    *,
    period: str | None = None,
    content_type: str | None = None,
) -> PlatformDashboardData:
    base = base_platform_visualizations_queryset(platform)
    base = filter_visualizations_by_period(base, period)
    filtered_base = filter_visualizations_by_content_type(base, content_type)

    report_kpis = compute_platform_report_kpis(filtered_base)
    clicks_per_genre = aggregate_clicks_per_genre(filtered_base)
    content_table = aggregate_content_clicks_table(filtered_base)
    top_films = aggregate_top_content_by_type(base, "film")
    top_series = aggregate_top_content_by_type(base, "serie")

    content_type_clicks = [
        {"label": "Pel.licules", "clicks": report_kpis["film_visualizations"]},
        {"label": "Series", "clicks": report_kpis["serie_visualizations"]},
    ]

    return PlatformDashboardData(
        platform_id=platform.id,
        platform_name=platform.name,
        catalog_kpis=PlatformCatalogKpis(**compute_platform_catalog_kpis(platform)),
        report_kpis=PlatformReportKpis(**report_kpis),
        clicks_per_genre=clicks_per_genre,
        content_type_clicks=content_type_clicks,
        top_genres=clicks_per_genre,
        content_table=content_table,
        top_films=top_films,
        top_series=top_series,
    )


def _horizontal_bar_chart_png_base64(
    rows: list[dict],
    *,
    label_key: str,
    value_key: str = "clicks",
    x_label: str = "Visualitzacions",
    color: str = "#e50914",
) -> str:
    if not rows:
        fig, ax = plt.subplots(figsize=(5.6, 2.1))
        ax.text(0.5, 0.5, "Sense dades", ha="center", va="center")
        ax.axis("off")
    else:
        labels = [row.get(label_key) or "Sense dades" for row in rows]
        values = [row[value_key] for row in rows]
        fig, ax = plt.subplots(figsize=(5.6, max(2.1, len(labels) * 0.28)))
        ax.barh(labels, values, color=color)
        ax.set_xlabel(x_label)
        ax.invert_yaxis()
        ax.tick_params(axis="y", labelsize=7)
        ax.tick_params(axis="x", labelsize=7)
        for i, value in enumerate(values):
            ax.text(value + 0.05, i, str(value), va="center", fontsize=7)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def _vertical_bar_chart_png_base64(
    rows: list[dict],
    *,
    label_key: str,
    value_key: str = "clicks",
    y_label: str = "Visualitzacions",
) -> str:
    if not rows:
        fig, ax = plt.subplots(figsize=(5.9, 3.0))
        ax.text(0.5, 0.5, "Sense dades", ha="center", va="center")
        ax.axis("off")
    else:
        labels = [row.get(label_key) or "Sense dades" for row in rows]
        values = [row[value_key] for row in rows]
        fig, ax = plt.subplots(figsize=(5.9, 3.1))
        bars = ax.bar(labels, values, color=_chart_colors(len(labels)))
        ax.set_ylabel(y_label)
        ax.set_ylim(top=max(values) * 1.18 if values else 1)
        ax.tick_params(axis="x", labelsize=7, rotation=32)
        ax.tick_params(axis="y", labelsize=7)
        ax.grid(axis="y", alpha=0.22)
        ax.bar_label(bars, padding=2, fontsize=7)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def _doughnut_chart_png_base64(
    rows: list[dict],
    *,
    label_key: str,
    value_key: str = "clicks",
) -> str:
    if not rows or not any(row.get(value_key, 0) for row in rows):
        fig, ax = plt.subplots(figsize=(4.2, 3.0))
        ax.text(0.5, 0.5, "Sense dades", ha="center", va="center")
        ax.axis("off")
    else:
        labels = [row.get(label_key) or "Sense dades" for row in rows]
        values = [row[value_key] for row in rows]
        fig, ax = plt.subplots(figsize=(4.2, 3.0))
        wedges, _ = ax.pie(
            values,
            colors=_chart_colors(len(values)),
            startangle=90,
            counterclock=False,
            wedgeprops={"width": 0.38, "edgecolor": "white"},
        )
        ax.text(
            0,
            0,
            str(sum(values)),
            ha="center",
            va="center",
            fontsize=14,
            fontweight="bold",
        )
        legend_labels = [
            f"{label}: {value}" for label, value in zip(labels, values)
        ]
        ax.legend(
            wedges,
            legend_labels,
            loc="center left",
            bbox_to_anchor=(0.88, 0.5),
            frameon=False,
            fontsize=7,
        )
        ax.set(aspect="equal")
        fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def genre_clicks_chart_png_base64(clicks_per_genre: list[dict]) -> str:
    """Bar chart of genre names vs visualizations."""
    rows = [
        {"label": row["genre__name"] or "Sense genere", "clicks": row["clicks"]}
        for row in clicks_per_genre
    ]
    return _vertical_bar_chart_png_base64(rows, label_key="label")


def content_type_chart_png_base64(content_type_clicks: list[dict]) -> str:
    return _doughnut_chart_png_base64(
        content_type_clicks,
        label_key="label",
    )


def top_genres_chart_png_base64(top_genres: list[dict]) -> str:
    rows = [
        {"label": row["genre__name"] or "Sense genere", "clicks": row["clicks"]}
        for row in top_genres[:8]
    ]
    return _horizontal_bar_chart_png_base64(rows, label_key="label")
