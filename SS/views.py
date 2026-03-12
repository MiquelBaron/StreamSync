from django.shortcuts import render
from SS.models import *
from SS.forms import *
from django.urls import reverse_lazy, reverse
from django.views.generic import CreateView


# Create your views here.


def home(request):
    return render(request, 'home.html',)


class register_view(CreateView):
    form_class = RegisterForm
    success_url = reverse_lazy("login")
    template_name = "register.html"

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from .forms import LoginForm

def login_view(request):
    form = LoginForm()
    error = None

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            try:
                user = User.objects.get(email=email)
                user = authenticate(request, username=user.username, password=password)
                if user is not None:
                    login(request, user)
                    return redirect('perfil')
                else:
                    error = "Les dades introduïdes no són correctes."
            except User.DoesNotExist:
                error = "Les dades introduïdes no són correctes."

    return render(request, 'login.html', {'form': form, 'error': error})


def register_view(request):
    form = RegisterForm()
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            return redirect('login')
    return render(request, 'register.html', {'form': form})