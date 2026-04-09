from typing import Any


from django.contrib.auth.models import Group
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect

class CustomLoginView(LoginView):
    template_name = "login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        return "/dashboard/"


class CustomLogoutView(LogoutView):
    next_page = "/login/"


class RegisterView(CreateView):
    template_name = "register.html"
    form_class = UserCreationForm
    success_url = reverse_lazy("login")
    def form_valid(self, form):
        response = super().form_valid(form)
        creator_group = Group.objects.get(name="Consumidor de contingut")
        self.object.groups.add(creator_group)
        return response


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard.html"
    login_url = "/login/"

def home_redirect(request):
    """
    Redirige la raíz '/' a '/dashboard'.
    """
    return redirect('/dashboard/')