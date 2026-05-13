from django.contrib.auth.models import User
from django.db import models

class Country(models.Model):
    name = models.CharField(max_length=100)
    iso_code = models.CharField(max_length=3, unique=True)
    source_platform = models.CharField(max_length=64, blank=True, default="")
    external_id = models.IntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source_platform", "external_id"],
                name="uniq_ss_country_platform_extid",
                condition=models.Q(external_id__isnull=False),
            ),
        ]

    def __str__(self):
        return self.name

class Platform(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class ContentConsumer(User):
    preferred_genres = models.ManyToManyField(
        "Genre",
        related_name="preferred_by_consumers",
        blank=True,
    )

    def __str__(self):
        return f"ContentConsumer({self.username})"


class PlataformManager(User):
    platform = models.ForeignKey(
        Platform,
        on_delete=models.CASCADE,
        related_name="platform_managers",
    )

    def __str__(self):
        return f"PlataformManager({self.username} -> {self.platform.name})"

class Genre(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    source_platform = models.CharField(max_length=64, blank=True, default="")
    external_id = models.IntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source_platform", "external_id"],
                name="uniq_ss_genre_platform_extid",
                condition=models.Q(external_id__isnull=False),
            ),
        ]

    def __str__(self):
        return self.name


class Director(models.Model):
    name = models.CharField(max_length=150)
    birth_date = models.DateField(blank=True, null=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True)
    created_at = models.DateField(auto_now_add=True)  # solo día/mes/año
    source_platform = models.CharField(max_length=64, blank=True, default="")
    external_id = models.IntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source_platform", "external_id"],
                name="uniq_ss_director_platform_extid",
                condition=models.Q(external_id__isnull=False),
            ),
        ]

    def __str__(self):
        return self.name


class AgeRating(models.Model):
    description = models.CharField(max_length=50)
    minimum_age = models.IntegerField()
    source_platform = models.CharField(max_length=64, blank=True, default="")
    external_id = models.IntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source_platform", "external_id"],
                name="uniq_ss_agerating_platform_extid",
                condition=models.Q(external_id__isnull=False),
            ),
        ]

    def __str__(self):
        return f"{self.description} ({self.minimum_age}+)"


class Language(models.Model):
    name = models.CharField(max_length=50)
    iso_code = models.CharField(max_length=3, unique=True)
    source_platform = models.CharField(max_length=64, blank=True, default="")
    external_id = models.IntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source_platform", "external_id"],
                name="uniq_ss_language_platform_extid",
                condition=models.Q(external_id__isnull=False),
            ),
        ]

    def __str__(self):
        return self.name


class Content(models.Model):
    platforms = models.ManyToManyField(Platform, related_name="contents", blank=True)
    title = models.CharField(max_length=255, unique=True)
    synopsis = models.TextField(blank=True, null=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1, blank=True, null=True)
    genre = models.ForeignKey(Genre, on_delete=models.PROTECT)
    director = models.ForeignKey(Director, on_delete=models.PROTECT)
    country = models.ForeignKey(Country, on_delete=models.PROTECT)
    language = models.ForeignKey(Language, on_delete=models.PROTECT)
    age_rating = models.ForeignKey(AgeRating, on_delete=models.PROTECT)
    expires_at = models.DateTimeField(null=True, blank=True)
    sync_external_ref = models.CharField(max_length=320, unique=True, null=True, blank=True, db_index=True)
    is_active = models.BooleanField(default=True)
    last_seen = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title


class Film(Content):
    year = models.IntegerField()
    release_date = models.DateField(blank=True, null=True)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)


class Serie(Content):
    start_year = models.IntegerField()
    end_year = models.IntegerField(blank=True, null=True)
    total_seasons = models.IntegerField()


class Incidence(models.Model):
    TECHNICAL = "technical"
    BILLING = "billing"
    ACCESS = "access"
    CONTENT = "content"
    OTHER = "other"
    TYPE_CHOICES = [
        (TECHNICAL, "Technical issue"),
        (BILLING, "Billing issue"),
        (ACCESS, "Access/login issue"),
        (CONTENT, "Content mismatch"),
        (OTHER, "Other"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="incidences")
    name = models.CharField(max_length=255)
    description = models.TextField()
    incidence_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=OTHER)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class Visualization(models.Model):
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="visualizations")
    viewed_at = models.DateTimeField()
    content = models.ForeignKey(Content, on_delete=models.CASCADE, related_name="visualizations")
    genre = models.ForeignKey(Genre, on_delete=models.PROTECT, related_name="visualizations")
    platform = models.ForeignKey(Platform, on_delete=models.PROTECT, related_name="visualizations")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "viewed_at"], name="unique_user_viewed_at")
        ]

    def __str__(self):
        return f"Visualization({self.user.username} @ {self.viewed_at})"


class Notification(models.Model):
    users = models.ManyToManyField(User, related_name="notifications", blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification({self.title})"




class ApiKey(models.Model):
    api_key = models.CharField(max_length=64, unique=True)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE, related_name="api_keys")
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.platform.name} - {self.api_key}"


class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews")
    content = models.ForeignKey(Content, on_delete=models.CASCADE, related_name="reviews")
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at'] # Les més recents primer

    def __str__(self):
        return f"Review de {self.user.username} sobre {self.content.title}"