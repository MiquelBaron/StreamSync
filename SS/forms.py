from django import forms
from django.contrib.auth.models import User

class LoginForm(forms.Form):
    email = forms.EmailField(label='Correu electrònic')
    password = forms.CharField(widget=forms.PasswordInput, label='Contrasenya')

class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label='Contrasenya')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Confirma la contrasenya')

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('password') != cleaned_data.get('password2'):
            raise forms.ValidationError("Les contrasenyes no coincideixen.")
        return cleaned_data