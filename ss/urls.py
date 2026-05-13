from django.urls import path
from .views import *

urlpatterns = [
    path("login/", CustomLoginView.as_view(), name="login"),
    path("register/", RegisterView.as_view(), name="register"),
    path("logout/", CustomLogoutView.as_view(), name="logout"),
        path('', home_redirect),  # raíz '/' redirige a /dashboard

    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("platform/analytics/", PlatformAnalyticsDashboardView.as_view(), name="platform_analytics_dashboard"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("preferences/", PreferencesView.as_view(), name="preferences" ),
    path("users/", UserManagementView.as_view(), name="user_management"),
    path("visualizations/register/", RegisterVisualizationView.as_view(), name="register_visualization"),
    path("incidences/report/", ReportIncidenceView.as_view(), name="report_incidence"),
    path("reports/platform-analytics.pdf", PlatformAnalyticsPdfView.as_view(), name="platform_analytics_pdf"),
    path("dashboard/director/", DirectorDashboardView.as_view(), name="director_dashboard"),
    path("reports/platform-analytics.csv", PlatformAnalyticsCsvView.as_view(), name="platform_analytics_csv"),
]
