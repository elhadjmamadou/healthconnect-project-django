# ==============================================================================
# disponibilites/urls.py — Routes de l'application disponibilités
# ==============================================================================
# app_name = 'disponibilites' : espace de noms pour les URLs.
# Dans les templates : {% url 'disponibilites:liste' %}, {% url 'disponibilites:ajouter' %}
#
# Toutes ces routes sont réservées aux médecins (MedecinRequiredMixin dans views.py).
# Un médecin ne peut gérer QUE ses propres créneaux (filtre medecin__user=request.user).
#
# Routes :
#
#   ''              → liste des créneaux du médecin connecté avec statistiques
#                     (libres, réservés, total)
#
#   ajouter/        → POST : crée un nouveau créneau de disponibilité
#                     La validation anti-chevauchement est dans Disponibilite.clean()
#
#   <pk>/modifier/  → POST : modifie un créneau existant (seulement si statut=LIBRE)
#                     Un créneau réservé ne peut pas être modifié car un RDV y est attaché
#
#   <pk>/supprimer/ → POST : supprime un créneau (seulement si statut=LIBRE)
#                     Même règle : un créneau réservé protège le RDV patient
#
# Note : pas de vue GET pour ajouter/modifier — les formulaires sont dans la page liste
# et les actions sont soumises en POST directement.
# ==============================================================================

from django.urls import path
from . import views

app_name = 'disponibilites'

urlpatterns = [
    # Liste des créneaux du médecin (avec KPIs et formulaire d'ajout inline)
    path('', views.ListeDisponibilitesView.as_view(), name='liste'),

    # Ajout d'un nouveau créneau (POST uniquement)
    path('ajouter/', views.AjouterDisponibiliteView.as_view(), name='ajouter'),

    # Modification et suppression d'un créneau existant (POST uniquement, si libre)
    path('<int:pk>/modifier/', views.ModifierDisponibiliteView.as_view(), name='modifier'),
    path('<int:pk>/supprimer/', views.SupprimerDisponibiliteView.as_view(), name='supprimer'),
]
