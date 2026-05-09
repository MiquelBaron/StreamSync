"""
Director General Dashboard Service
===================================
Responsabilitat: obtenir i preparar totes les dades del dashboard
del Director General. La view només ha de cridar aquesta classe.

IMPORTANT: La view ha de verificar que l'usuari té rol de Director
General ABANS de cridar aquest servei.
"""

from django.db.models import Count
from django.utils import timezone
from datetime import timedelta

from ss.models import (
    Content,
    Film,
    Serie,
    Platform,
    Visualization,
    Genre,
    ContentConsumer,
)


class DirectorDashboardService:
    """
    Obté i prepara les dades del dashboard pel Director General.

    Ús des de la view:
        service = DirectorDashboardService(filters)
        context = service.get_dashboard_context()
    """

    # ------------------------------------------------------------------ #
    #  Constants per als filtres temporals                                 #
    # ------------------------------------------------------------------ #
    PERIOD_DAYS = {
        "day":   1,
        "week":  7,
        "month": 30,
    }

    def __init__(self, filters: dict | None = None):
        """
        filters pot contenir:
          - period:   'day' | 'week' | 'month' | None  (cap filtre temporal)
          - content_type: 'film' | 'serie' | None       (tots dos)
          - platform_id:  int | None                    (totes les plataformes)
        """
        self.filters = filters or {}
        self._visualizations_qs = self._build_base_queryset()

    # ------------------------------------------------------------------ #
    #  Punt d'entrada principal                                            #
    # ------------------------------------------------------------------ #
    def get_dashboard_context(self) -> dict:
        """
        Retorna un diccionari llest per passar a la template.
        """
        return {
            # KPIs
            "kpis": self._get_kpis(),

            # Dades per als gràfics (format JSON-safe per a Chart.js)
            "charts": {
                "visualizations_by_genre":    self._get_visualizations_by_genre(),
                "visualizations_by_type":     self._get_visualizations_by_type(),
                "top_genres":                 self._get_top_genres(),
                "visualizations_by_platform": self._get_visualizations_by_platform(),
            },

            # Llistes (per si la template les necessita)
            "lists": {
                "films":  self._get_films_list(),
                "series": self._get_series_list(),
            },

            # Filtres actuals (perquè la template pugui mostrar l'estat dels filtres)
            "active_filters": self.filters,

            # Opcions de filtre disponibles
            "filter_options": {
                "platforms": list(Platform.objects.values("id", "name")),
            },
        }

    # ------------------------------------------------------------------ #
    #  KPIs                                                                #
    # ------------------------------------------------------------------ #
    def _get_kpis(self) -> dict:
        return {
            "total_films":    Film.objects.count(),
            "total_series":   Serie.objects.count(),
            "total_content":  Film.objects.count() + Serie.objects.count(),
            "total_platforms": Platform.objects.count(),
            "total_consumers": ContentConsumer.objects.count(),
        }

    # ------------------------------------------------------------------ #
    #  Gràfics                                                             #
    # ------------------------------------------------------------------ #
    def _get_visualizations_by_genre(self) -> dict:
        """
        Gràfic de barres: visualitzacions per gènere.
        Retorna {'labels': [...], 'data': [...]}
        """
        qs = (
            self._visualizations_qs
            .values("genre__name")
            .annotate(total=Count("id"))
            .order_by("-total")
        )
        return {
            "labels": [row["genre__name"] for row in qs],
            "data":   [row["total"] for row in qs],
        }

    def _get_visualizations_by_type(self) -> dict:
        """
        Gràfic de pastís: visualitzacions de sèries vs pel·lícules.
        Retorna {'labels': [...], 'data': [...]}
        """
        film_ids  = Film.objects.values_list("content_ptr_id", flat=True)
        serie_ids = Serie.objects.values_list("content_ptr_id", flat=True)

        film_count  = self._visualizations_qs.filter(content_id__in=film_ids).count()
        serie_count = self._visualizations_qs.filter(content_id__in=serie_ids).count()

        return {
            "labels": ["Pel·lícules", "Sèries"],
            "data":   [film_count, serie_count],
        }

    def _get_top_genres(self) -> dict:
        """
        Gràfic de gèneres més consumits, ordenats de més a menys.
        Retorna {'labels': [...], 'data': [...]}
        """
        # Reutilitzem _get_visualizations_by_genre (ja ve ordenat)
        return self._get_visualizations_by_genre()

    def _get_visualizations_by_platform(self) -> dict:
        """
        Gràfic de barres: visualitzacions totals per plataforma.
        Retorna {'labels': [...], 'data': [...]}
        """
        qs = (
            self._visualizations_qs
            .values("platform__name")
            .annotate(total=Count("id"))
            .order_by("-total")
        )
        return {
            "labels": [row["platform__name"] for row in qs],
            "data":   [row["total"] for row in qs],
        }

    # ------------------------------------------------------------------ #
    #  Llistes                                                             #
    # ------------------------------------------------------------------ #
    def _get_films_list(self) -> list:
        """Llista de totes les pel·lícules."""
        return list(
            Film.objects.select_related("genre", "director")
            .values("id", "title", "year", "genre__name", "director__name", "rating")
        )

    def _get_series_list(self) -> list:
        """Llista de totes les sèries."""
        return list(
            Serie.objects.select_related("genre", "director")
            .values("id", "title", "start_year", "end_year",
                    "total_seasons", "genre__name", "director__name", "rating")
        )

    # ------------------------------------------------------------------ #
    #  Construcció del queryset base amb filtres aplicats                  #
    # ------------------------------------------------------------------ #
    def _build_base_queryset(self):
        """
        Aplica els filtres de període, tipus de contingut i plataforma
        al queryset de Visualization. La resta de mètodes parteixen d'aquí.
        """
        qs = Visualization.objects.all()

        # Filtre temporal
        period = self.filters.get("period")
        if period and period in self.PERIOD_DAYS:
            cutoff = timezone.now() - timedelta(days=self.PERIOD_DAYS[period])
            qs = qs.filter(viewed_at__gte=cutoff)

        # Filtre per tipus de contingut
        content_type = self.filters.get("content_type")
        if content_type == "film":
            film_ids = Film.objects.values_list("content_ptr_id", flat=True)
            qs = qs.filter(content_id__in=film_ids)
        elif content_type == "serie":
            serie_ids = Serie.objects.values_list("content_ptr_id", flat=True)
            qs = qs.filter(content_id__in=serie_ids)

        # Filtre per plataforma
        platform_id = self.filters.get("platform_id")
        if platform_id:
            qs = qs.filter(platform_id=platform_id)

        return qs