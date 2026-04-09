from django import forms

from .models import Genre


AGE_RATING_CHOICES = [
    (0, "+0"),
    (13, "+13"),
    (18, "+18"),
    (21, "+21"),
]


class ContentSearchForm(forms.Form):
    title = forms.CharField(
        label="Titol",
        max_length=255,
        required=False,
        strip=True,
    )
    director = forms.CharField(
        label="Director",
        max_length=150,
        required=False,
        strip=True,
    )
    genre = forms.ModelChoiceField(
        label="Genere",
        queryset=Genre.objects.order_by("name"),
        required=False,
        empty_label="Tots els generes",
    )
    age_rating = forms.TypedChoiceField(
        label="Edat minima",
        choices=AGE_RATING_CHOICES,
        required=False,
        coerce=int,
        empty_value=0,
        initial=0,
    )

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data["title"] = (cleaned_data.get("title") or "").strip()
        cleaned_data["director"] = (cleaned_data.get("director") or "").strip()

        if cleaned_data.get("age_rating") in (None, ""):
            cleaned_data["age_rating"] = 0

        return cleaned_data
