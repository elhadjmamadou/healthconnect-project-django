from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "rapports"

urlpatterns = [
    path("liste/", views.ListeRapportsView.as_view(), name="liste"),
    path("generer/", views.GenererRapportView.as_view(), name="generer"),
    path("<int:pk>/telecharger/", views.TelechargerRapportView.as_view(), name="telecharger"),
    path("<int:pk>/supprimer/", views.SupprimerRapportView.as_view(), name="supprimer"),
    path("dashboard/", RedirectView.as_view(pattern_name="rapports:liste"), name="dashboard_admin"),
]