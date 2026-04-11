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
    ApiKey,
    ContentConsumer,
)

admin.site.register(Country)
admin.site.register(Platform)
admin.site.register(Genre)
admin.site.register(Director)
admin.site.register(AgeRating)
admin.site.register(Language)
@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ("title", "year", "director", "genre", "rating")
admin.site.register(Series)
admin.site.register(ApiKey)
admin.site.register(ContentConsumer)