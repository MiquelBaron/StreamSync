from django import forms

from .models import Genre
from .models import AgeRating

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
    age_rating = forms.ModelChoiceField(
        label="Edat minima",
        queryset=AgeRating.objects.order_by("minimum_age"),
        required=False,
        empty_label="Totes les edats",
    )

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data["title"] = (cleaned_data.get("title") or "").strip()
        cleaned_data["director"] = (cleaned_data.get("director") or "").strip()


        return cleaned_data
