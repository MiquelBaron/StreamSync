from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from .models import Genre, ContentConsumer, Platform, Incidence
from .models import AgeRating
from .roles import ROLE_DEFINITIONS


def app_role_groups():
    return Group.objects.filter(name__in=ROLE_DEFINITIONS.values()).order_by("name")

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


class IncidenceForm(forms.ModelForm):
    class Meta:
        model = Incidence
        fields = ["name", "description"]
        labels = {
            "name": "Titol",
            "description": "Descripcio",
        }
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "incidence-modal__input",
                    "placeholder": "Resumeix la incidencia",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "incidence-modal__textarea",
                    "placeholder": "Explica que ha passat",
                    "rows": 5,
                }
            ),
        }


class UserRoleFilterForm(forms.Form):
    role = forms.ModelChoiceField(
        label="Rol",
        queryset=Group.objects.none(),
        required=False,
        empty_label="Tots els rols",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].queryset = app_role_groups()


class UserCreateForm(forms.Form):
    username = forms.CharField(
        label="Nom d'usuari",
        max_length=150,
        required=True,
    )
    first_name = forms.CharField(
        label="Nom",
        max_length=150,
        required=False,
    )
    last_name = forms.CharField(
        label="Cognoms",
        max_length=150,
        required=False,
    )
    email = forms.EmailField(
        label="Correu electronic",
        required=False,
    )
    password = forms.CharField(
        label="Contrasenya",
        widget=forms.PasswordInput,
        required=True,
    )
    role = forms.ModelChoiceField(
        label="Rol",
        queryset=Group.objects.none(),
        required=True,
        empty_label="Selecciona un rol",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].queryset = app_role_groups()

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        User = get_user_model()
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Ja existeix un usuari amb aquest nom.")
        return username

    def save(self):
        User = get_user_model()
        user = User(
            username=self.cleaned_data["username"],
            first_name=self.cleaned_data["first_name"],
            last_name=self.cleaned_data["last_name"],
            email=self.cleaned_data["email"],
            is_active=True,
            is_staff=False,
            is_superuser=False,
        )
        user.set_password(self.cleaned_data["password"])
        user.save()

        user.groups.set([self.cleaned_data["role"]])

        return user


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
