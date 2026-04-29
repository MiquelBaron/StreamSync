from django.contrib import admin
from .models import (
    Country,
    Platform,
    Content,
    Genre,
    Director,
    AgeRating,
    Language,
    Film,
    Serie,
    ApiKey,
    ContentConsumer,
    PlataformManager,
    Incidence,
    Visualization,
    Notification,
)

admin.site.register(Country)
admin.site.register(Platform)
admin.site.register(Genre)
admin.site.register(Director)
admin.site.register(AgeRating)
admin.site.register(Language)
@admin.register(Film)
class FilmAdmin(admin.ModelAdmin):
    list_display = ("title", "year", "director", "genre", "rating")
admin.site.register(Content)
admin.site.register(Serie)
admin.site.register(ApiKey)
admin.site.register(ContentConsumer)
admin.site.register(PlataformManager)
admin.site.register(Incidence)
admin.site.register(Visualization)
admin.site.register(Notification)