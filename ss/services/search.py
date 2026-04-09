from dataclasses import dataclass

from ..models import Movie, Series


@dataclass
class SearchCriteria:
    title: str | None = None
    director_query: str | None = None
    genre_id: int | None = None
    min_age: int | None = None


class DatabaseContentSearchService:
    def search(self, criteria: SearchCriteria) -> list[dict]:
        movies = self._serialize_results(self._apply_filters(Movie.objects.all(), criteria), "Pelicula")
        series = self._serialize_results(self._apply_filters(Series.objects.all(), criteria), "Serie")
        combined_results = movies + series
        return sorted(combined_results, key=lambda item: item["title"].lower())

    def _apply_filters(self, queryset, criteria: SearchCriteria):
        queryset = queryset.select_related(
            "director",
            "genre",
            "age_rating",
            "country",
            "language",
        ).prefetch_related("platforms")

        if criteria.title:
            queryset = queryset.filter(title__icontains=criteria.title)

        if criteria.director_query:
            queryset = queryset.filter(director__name__icontains=criteria.director_query)

        if criteria.genre_id:
            queryset = queryset.filter(genre_id=criteria.genre_id)

        if criteria.min_age is not None:
            queryset = queryset.filter(age_rating__minimum_age__gte=criteria.min_age)

        return queryset

    def _serialize_results(self, queryset, content_type: str) -> list[dict]:
        serialized = []
        for item in queryset:
            serialized.append(
                {
                    "title": item.title,
                    "content_type": content_type,
                    "director": item.director.name,
                    "genre": item.genre.name,
                    "minimum_age": item.age_rating.minimum_age,
                    "rating_label": item.age_rating.description,
                    "platforms": ", ".join(platform.name for platform in item.platforms.all()) or "-",
                }
            )
        return serialized
