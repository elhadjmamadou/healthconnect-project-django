# ==============================================================================
# rendez_vous/urls.py — Routes de l'application rendez-vous
# ==============================================================================
# app_name = 'rendez_vous' : espace de noms pour les URLs.
# Dans les templates : {% url 'rendez_vous:reserver' %}, {% url 'rendez_vous:detail' pk=rdv.pk %}
#
# Cycle de vie d'un rendez-vous et les routes correspondantes :
#
#   1. reserver/     → wizard 3 étapes en session :
#                       étape 1 : choisir le médecin (action=select_medecin)
#                       étape 2 : choisir le créneau (action=select_dispo)
#                       étape 3 : confirmer et créer le RDV (action=confirmer)
#
#   2. <pk>/         → afficher le détail d'un RDV (patient ou médecin)
#
#   3. <pk>/confirmer/ → le médecin accepte le RDV (statut → CONFIRME)
#      <pk>/refuser/   → le médecin refuse le RDV (statut → REFUSE)
#      <pk>/annuler/   → le patient ou le médecin annule (statut → ANNULE)
#
#   ''               → liste de tous les RDV (filtrée selon le rôle dans la vue)
#
# Note : toutes ces vues exigent une connexion (LoginRequiredMixin).
# La liste est filtrée selon le rôle : un patient voit ses propres RDV,
# un médecin voit les RDV de sa patientèle, un admin voit tout.
# ==============================================================================

from django.urls import path
from . import views

app_name = 'rendez_vous'

urlpatterns = [
    # Liste des rendez-vous (filtrée selon le rôle de l'utilisateur)
    path('', views.ListeRDVView.as_view(), name='liste'),

    # Wizard de réservation (3 étapes via paramètres POST et session)
    path('reserver/', views.ReservationRDVView.as_view(), name='reserver'),

    # Détail d'un rendez-vous spécifique
    path('<int:pk>/', views.DetailRDVView.as_view(), name='detail'),

    # Actions de gestion du cycle de vie d'un RDV
    path('<int:pk>/confirmer/', views.ConfirmerRDVView.as_view(), name='confirmer'),  # médecin accepte
    path('<int:pk>/refuser/', views.RefuserRDVView.as_view(), name='refuser'),        # médecin refuse
    path('<int:pk>/annuler/', views.AnnulerRDVView.as_view(), name='annuler'),        # annulation
]
