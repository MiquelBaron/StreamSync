from dataclasses import dataclass

from .models import Movie, Series, AgeRating


@dataclass
class SearchCriteria:
    title: str | None = None
    director_query: str | None = None
    genre_id: int | None = None
    min_age: AgeRating | None = None


class DatabaseContentSearchService:
    def search(self, criteria: SearchCriteria) -> list:
        movies = list(self._apply_filters(Movie.objects.all(), criteria))
        series = list(self._apply_filters(Series.objects.all(), criteria))
        combined_results = movies + series
        return sorted(combined_results, key=lambda item: item.title.lower())



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
            queryset = queryset.filter(age_rating__minimum_age__gte=criteria.min_age.minimum_age)

        return queryset

   
