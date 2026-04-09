from django.contrib import admin
from .models import (
    Country,
    Platform,
    Genre,
    Director,
    AgeRating,
    Language,
    Movie,
    Series,
    ApiKey
)

admin.site.register(Country)
admin.site.register(Platform)
admin.site.register(Genre)
admin.site.register(Director)
admin.site.register(AgeRating)
admin.site.register(Language)
admin.site.register(Movie)
admin.site.register(Series)
admin.site.register(ApiKey)