# ==============================================================================
# rapports/urls.py — Routes de l'application rapports
# ==============================================================================
# app_name = 'rapports' : espace de noms pour les URLs.
# Dans les templates : {% url 'rapports:dashboard_admin' %}, {% url 'rapports:generer' %}
#
# Toutes ces routes sont réservées aux administrateurs (AdminRequiredMixin dans views.py).
#
# Routes :
#
#   dashboard/          → DashboardAdminView : tableau de bord avec KPIs globaux,
#                         graphiques Chart.js (RDV par jour, revenus par mois)
#                         et statistiques en temps réel calculées depuis la BDD.
#
#   liste/              → ListeRapportsView : historique des rapports générés.
#
#   generer/            → GenererRapportView : formulaire de sélection (type + période)
#                         puis calcul des statistiques et création d'un RapportGenere.
#
#   <pk>/telecharger/   → TelechargerRapportView : téléchargement du fichier exporté
#                         (FileResponse avec le fichier stocké dans MEDIA_ROOT/rapports/).
#
#   <pk>/supprimer/     → SupprimerRapportView : supprime le RapportGenere et son fichier.
#
# Note : 'dashboard/' est volontairement la première route (nom le plus utilisé
# car c'est la page d'atterrissage des admins après connexion).
# ==============================================================================

from django.urls import path
from . import views

app_name = "rapports"

urlpatterns = [
    # Tableau de bord principal admin (KPIs + graphiques Chart.js)
    path("dashboard/", views.DashboardAdminView.as_view(), name="dashboard_admin"),

    # Historique et gestion des rapports générés
    path("liste/", views.ListeRapportsView.as_view(), name="liste"),
    path("generer/", views.GenererRapportView.as_view(), name="generer"),

    # Actions sur un rapport existant
    path("<int:pk>/telecharger/", views.TelechargerRapportView.as_view(), name="telecharger"),
    path("<int:pk>/supprimer/", views.SupprimerRapportView.as_view(), name="supprimer"),
]
