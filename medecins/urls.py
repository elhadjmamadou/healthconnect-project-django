# ==============================================================================
# medecins/urls.py — Routes de l'application médecins
# ==============================================================================
# app_name = 'medecins' : espace de noms pour les URLs.
# Dans les templates : {% url 'medecins:liste' %}, {% url 'medecins:detail' pk=1 %}
#
# Deux catégories de routes :
#
# PUBLIQUES (sans login) :
#   annuaire/           → liste des médecins visible par les patients non connectés
#   annuaire/<pk>/      → fiche publique d'un médecin (biographie + disponibilités)
#
# ADMIN (login requis, rôle admin) :
#   ''                  → liste interne de tous les médecins (gestion admin)
#   creer/              → formulaire de création d'un médecin
#   <pk>/               → fiche détaillée côté admin
#   <pk>/modifier/      → formulaire de modification
#   <pk>/supprimer/     → suppression du compte médecin
#   dashboard/          → tableau de bord du médecin connecté
#
# SPÉCIALITÉS (gestion par l'admin) :
#   specialites/            → liste des spécialités
#   specialites/creer/      → ajout d'une spécialité
#   specialites/<pk>/supprimer/ → suppression d'une spécialité
#
# Ordre des routes : 'annuaire/' doit être AVANT '<int:pk>/' pour ne pas
# être capturée par le pattern dynamique.
# ==============================================================================

from django.urls import path
from . import views

app_name = 'medecins'

urlpatterns = [
    # Tableau de bord du médecin connecté (MedecinRequiredMixin)
    path('dashboard/', views.DashboardMedecinView.as_view(), name='dashboard'),

    # Annuaire public : accessible sans connexion (pas de LoginRequired)
    path('annuaire/', views.AnnuaireView.as_view(), name='annuaire'),
    path('annuaire/<int:pk>/', views.AnnuaireDetailView.as_view(), name='annuaire_detail'),

    # Gestion admin des médecins
    path('', views.ListeMedecinsView.as_view(), name='liste'),
    path('creer/', views.CreerMedecinView.as_view(), name='creer'),
    path('<int:pk>/', views.DetailMedecinView.as_view(), name='detail'),
    path('<int:pk>/modifier/', views.ModifierMedecinView.as_view(), name='modifier'),
    path('<int:pk>/supprimer/', views.SupprimerMedecinView.as_view(), name='supprimer'),

    # Gestion des spécialités médicales
    path('specialites/', views.ListeSpecialitesView.as_view(), name='specialites'),
    path('specialites/creer/', views.CreerSpecialiteView.as_view(), name='creer_specialite'),
    path('specialites/<int:pk>/supprimer/', views.SupprimerSpecialiteView.as_view(), name='supprimer_specialite'),
]
