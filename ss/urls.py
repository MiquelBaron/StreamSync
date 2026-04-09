from django.urls import path
from .views import *

urlpatterns = [
    path("login/", CustomLoginView.as_view(), name="login"),
    path("register/", RegisterView.as_view(), name="register"),
    path("logout/", CustomLogoutView.as_view(), name="logout"),
        path('', home_redirect),  # raíz '/' redirige a /dashboard

    path("dashboard/", DashboardView.as_view(), name="dashboard"),
]