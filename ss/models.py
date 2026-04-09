from django.db import models

# ss/models.py
from django.db import models

class Country(models.Model):
    name = models.CharField(max_length=100)
    iso_code = models.CharField(max_length=3, unique=True)

    def __str__(self):
        return self.name

class Platform(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class Genre(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Director(models.Model):
    name = models.CharField(max_length=150)
    birth_date = models.DateField(blank=True, null=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True)
    created_at = models.DateField(auto_now_add=True)  # solo día/mes/año

    def __str__(self):
        return self.name

class AgeRating(models.Model):
    description = models.CharField(max_length=50)
    minimum_age = models.IntegerField()

    def __str__(self):
        return f"{self.description} ({self.minimum_age}+)"

class Language(models.Model):
    name = models.CharField(max_length=50)
    iso_code = models.CharField(max_length=3, unique=True)

    def __str__(self):
        return self.name

class Movie(models.Model):
    platforms = models.ManyToManyField(Platform, related_name="movies", blank=True)
    title = models.CharField(max_length=255, unique=True)
    synopsis = models.TextField(blank=True, null=True)
    year = models.IntegerField()
    release_date = models.DateField(blank=True, null=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1, blank=True, null=True)
    genre = models.ForeignKey(Genre, on_delete=models.PROTECT)
    director = models.ForeignKey(Director, on_delete=models.PROTECT)
    country = models.ForeignKey(Country, on_delete=models.PROTECT)
    language = models.ForeignKey(Language, on_delete=models.PROTECT)
    age_rating = models.ForeignKey(AgeRating, on_delete=models.PROTECT)
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title

class Series(models.Model):
    platforms = models.ManyToManyField(Platform, related_name="series", blank=True)
    title = models.CharField(max_length=255, unique=True)
    synopsis = models.TextField(blank=True, null=True)
    start_year = models.IntegerField()
    end_year = models.IntegerField(blank=True, null=True)
    total_seasons = models.IntegerField()
    rating = models.DecimalField(max_digits=3, decimal_places=1, blank=True, null=True)
    genre = models.ForeignKey(Genre, on_delete=models.PROTECT)
    director = models.ForeignKey(Director, on_delete=models.PROTECT)
    country = models.ForeignKey(Country, on_delete=models.PROTECT)
    language = models.ForeignKey(Language, on_delete=models.PROTECT)
    age_rating = models.ForeignKey(AgeRating, on_delete=models.PROTECT)
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title




class ApiKey(models.Model):
    api_key = models.CharField(max_length=64, unique=True)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE, related_name="api_keys")
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.platform.name} - {self.api_key}"
