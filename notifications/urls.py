# ==============================================================================
# notifications/urls.py — Routes de l'application notifications
# ==============================================================================
# app_name = 'notifications' : espace de noms pour les URLs.
# Dans les templates : {% url 'notifications:liste' %}, {% url 'notifications:marquer_lu' pk=n.pk %}
#
# Routes :
#
#   ''                    → liste paginée de toutes les notifications de l'utilisateur
#   <pk>/lire/            → marque une notification comme lue (POST, réponse JSON)
#   <pk>/supprimer/       → supprime une notification (POST)
#   tout-lire/            → marque TOUTES les notifications non lues (bulk UPDATE)
#
# Ordre important :
#   'tout-lire/' doit être avant '' et avant '<int:pk>/lire/' pour éviter
#   que Django ne tente d'interpréter "tout-lire" comme un entier <pk>.
#   Django teste les patterns dans l'ordre et s'arrête au premier match.
#
# Toutes ces vues requièrent une connexion (LoginRequiredMixin dans views.py).
# Les vues filtrent également sur utilisateur=request.user pour la sécurité.
# ==============================================================================

from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # Route placée en premier pour éviter de masquer '' ou '<pk>/'
    path('tout-lire/', views.MarquerToutLuView.as_view(), name='tout_lire'),

    # Liste principale des notifications (paginée, 20 par page)
    path('', views.ListeNotificationsView.as_view(), name='liste'),

    # Actions sur une notification individuelle
    path('<int:pk>/lire/', views.MarquerLuView.as_view(), name='marquer_lu'),
    path('<int:pk>/supprimer/', views.SupprimerNotificationView.as_view(), name='supprimer'),
]
