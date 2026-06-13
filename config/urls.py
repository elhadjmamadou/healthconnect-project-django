# ==============================================================================
# config/urls.py — Point d'entrée global des URLs de HealthConnect
# ==============================================================================
# Ce fichier est le routeur principal de l'application Django.
# Django le charge en premier pour chaque requête HTTP (défini par ROOT_URLCONF
# dans base.py : ROOT_URLCONF = 'config.urls').
#
# Fonctionnement :
#   Django lit urlpatterns de haut en bas et s'arrête au premier match.
#   Chaque include() délègue le reste de l'URL à l'URLconf de l'app concernée.
#
# Exemple : requête GET /medecins/annuaire/
#   1. Django lit urlpatterns
#   2. "medecins/" → match ! → délègue "/annuaire/" à medecins/urls.py
#   3. medecins/urls.py : "annuaire/" → match → AnnuaireView
#
# include() avec namespace :
#   Le namespace doit correspondre à app_name dans l'URLconf de l'app.
#   Cela permet d'utiliser {% url 'medecins:annuaire' %} dans les templates.
#
# static(MEDIA_URL, document_root=MEDIA_ROOT) :
#   Sert les fichiers uploadés (photos de profil, fichiers de rapports)
#   via Django en DÉVELOPPEMENT uniquement.
#   En production, un serveur web (Nginx/Caddy) sert directement MEDIA_ROOT.
#   Cette ligne est inopérante si DEBUG=False.
# ==============================================================================

from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

# LandingView est importée ici (pas via include) car elle n'a pas d'app_name
from users.views import LandingView

urlpatterns = [
    # Interface d'administration Django (accès réservé aux superusers)
    path("admin/", admin.site.urls),

    # Authentification et profil utilisateur
    path("users/", include("users.urls", namespace="users")),

    # Gestion des patients et de leur espace personnel
    path("patients/", include("patients.urls", namespace="patients")),

    # Gestion des médecins (annuaire public + espace médecin + admin)
    path("medecins/", include("medecins.urls", namespace="medecins")),

    # Système de réservation de rendez-vous (wizard 3 étapes)
    path("rendez-vous/", include("rendez_vous.urls", namespace="rendez_vous")),

    # Consultations médicales et ordonnances numériques
    path("consultations/", include("consultations.urls", namespace="consultations")),

    # Créneaux de disponibilité des médecins
    path("disponibilites/", include("disponibilites.urls", namespace="disponibilites")),

    # Paiements en ligne via Djomy + webhook de confirmation
    path("paiements/", include("paiements.urls", namespace="paiements")),

    # Centre de notifications utilisateur
    path("notifications/", include("notifications.urls", namespace="notifications")),

    # Rapports statistiques et tableau de bord admin
    path("rapports/", include("rapports.urls", namespace="rapports")),

    # Page d'accueil publique (landing page) — doit être en dernier
    # pour ne pas capturer toutes les URLs non matchées
    path("", LandingView.as_view(), name="home"),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
# + static(...) : ajoute le service des fichiers MEDIA en développement (DEBUG=True)
# En production (DEBUG=False), cette liste est vide (Nginx/Caddy sert MEDIA)
