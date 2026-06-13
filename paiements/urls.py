# ==============================================================================
# paiements/urls.py — Routes de l'application paiements
# ==============================================================================
# app_name = 'paiements' : espace de noms pour les URLs.
# Dans les templates : {% url 'paiements:payer_rdv' pk=rdv.pk %}
#
# Routes :
#
#   ''                      → liste de tous les paiements (admin)
#   <pk>/                   → détail d'un paiement spécifique
#   <pk>/succes/            → page de confirmation affichée après paiement réussi
#   payer/rdv/<pk>/         → page de paiement pour un rendez-vous donné
#                             PayerRDVView lit le RDV, simule le paiement Djomy
#                             et redirige vers la page succes/
#
#   webhook/djomy/          → endpoint POST appelé par Djomy après confirmation
#                             NE PAS protéger avec CSRF (appel externe automatique)
#                             La sécurité est assurée par la signature HMAC-SHA256
#                             vérifiée dans WebhookDjomyView.
#
# CSRF et webhooks :
#   Django vérifie le token CSRF sur toutes les requêtes POST.
#   Pour le webhook (appelé par Djomy, pas par un navigateur), la vue utilise
#   @csrf_exempt (dans views.py) pour bypasser cette vérification.
#   La sécurité est remplacée par la vérification HMAC de la signature Djomy.
# ==============================================================================

from django.urls import path
from . import views

app_name = 'paiements'

urlpatterns = [
    # Liste et détail des paiements (admin)
    path('', views.ListePaiementsView.as_view(), name='liste'),
    path('<int:pk>/', views.DetailPaiementView.as_view(), name='detail'),

    # Page de confirmation affichée après un paiement réussi
    path('<int:pk>/succes/', views.PaiementSuccesView.as_view(), name='succes'),

    # Initiation du paiement pour un rendez-vous
    path('payer/rdv/<int:pk>/', views.PayerRDVView.as_view(), name='payer_rdv'),

    # Webhook Djomy : endpoint POST pour les notifications de paiement externes
    # Pas de CSRF (appel machine-à-machine), sécurisé par HMAC-SHA256
    path('webhook/djomy/', views.WebhookDjomyView.as_view(), name='webhook_djomy'),
]
