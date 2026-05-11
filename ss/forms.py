from django import forms

from .models import Genre, ContentConsumer, Platform
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



class PreferencesForm(forms.ModelForm):
    preferred_genres = forms.ModelMultipleChoiceField(
        queryset=Genre.objects.all(),
        widget=forms.CheckboxSelectMultiple, # Pots usar SelectMultiple si prefereixes
        required=False,
        label="Selecciona els teus gèneres preferits (màxim 3)"
    )

    class Meta:
        model = ContentConsumer
        fields = ['preferred_genres']

    def clean_preferred_genres(self):
        genres = self.cleaned_data.get('preferred_genres')
        if genres and genres.count() > 3:
            raise forms.ValidationError("Només pots seleccionar un màxim de 3 gèneres.")
        return genres


class PlatformAnalyticsFilterForm(forms.Form):
    PERIOD_CHOICES = [
        ("", "Tot l'historial"),
        ("day", "Avui"),
        ("week", "Setmana"),
        ("month", "Mes"),
        ("days", "Ultims 7 dies"),
        ("weeks", "Ultimes 4 setmanes"),
        ("months", "Ultims 12 mesos"),
    ]

    CONTENT_TYPE_CHOICES = [
        ("", "Series i pel.licules"),
        ("film", "Pel.licules"),
        ("serie", "Series"),
    ]

    period = forms.ChoiceField(
        label="Periode",
        choices=PERIOD_CHOICES,
        required=False,
    )
    content_type = forms.ChoiceField(
        label="Tipus",
        choices=CONTENT_TYPE_CHOICES,
        required=False,
    )
    platform = forms.ModelChoiceField(
        label="Plataforma",
        queryset=Platform.objects.none(),
        required=True,
    )

    def __init__(self, *args, platform=None, **kwargs):
        super().__init__(*args, **kwargs)
        if platform is not None:
            self.fields["platform"].queryset = Platform.objects.filter(pk=platform.pk)
            self.fields["platform"].initial = platform
