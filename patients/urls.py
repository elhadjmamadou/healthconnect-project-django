# ==============================================================================
# patients/urls.py — Routes de l'application patients
# ==============================================================================
# app_name = 'patients' : espace de noms pour les URLs.
# Dans les templates : {% url 'patients:dashboard' %}, {% url 'patients:detail' pk=p.pk %}
#
# Deux niveaux d'accès :
#
# PATIENT CONNECTÉ :
#   dashboard/  → DashboardPatientView (PatientRequiredMixin)
#                 Tableau de bord personnel : prochain RDV, statistiques, historique
#
# ADMIN :
#   ''           → liste de tous les patients avec recherche et filtres
#   creer/       → création d'un compte patient (User + profil)
#   <pk>/        → fiche complète d'un patient
#   <pk>/modifier/  → modification du compte et du profil
#   <pk>/supprimer/ → suppression en cascade (User + Patient + données liées)
#
# Ordre des routes : 'dashboard/' et 'creer/' doivent être placées AVANT '<int:pk>/'
# pour éviter que Django n'essaie d'interpréter "dashboard" ou "creer" comme un entier.
# ==============================================================================

from django.urls import path
from . import views

app_name = 'patients'

urlpatterns = [
    # Tableau de bord personnel du patient (accès patient uniquement)
    path('dashboard/', views.DashboardPatientView.as_view(), name='dashboard'),

    # Gestion admin des patients
    path('', views.ListePatientsView.as_view(), name='liste'),
    path('creer/', views.CreerPatientView.as_view(), name='creer'),
    path('<int:pk>/', views.DetailPatientView.as_view(), name='detail'),
    path('<int:pk>/modifier/', views.ModifierPatientView.as_view(), name='modifier'),
    path('<int:pk>/supprimer/', views.SupprimerPatientView.as_view(), name='supprimer'),
]
