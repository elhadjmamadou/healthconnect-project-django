from django.urls import path

from . import views

app_name = "rapports"

urlpatterns = [
    path("dashboard/", views.DashboardAdminView.as_view(), name="dashboard_admin"),
    path("liste/", views.ListeRapportsView.as_view(), name="liste"),
    path("generer/", views.GenererRapportView.as_view(), name="generer"),
    path("<int:pk>/telecharger/", views.TelechargerRapportView.as_view(), name="telecharger"),
    path("<int:pk>/supprimer/", views.SupprimerRapportView.as_view(), name="supprimer"),
]