# ==============================================================================
# config/settings/prod.py — Configuration de production
# ==============================================================================
# Ce fichier surcharge config/settings/base.py pour la mise en production.
# Il est activé en définissant la variable d'environnement :
#   DJANGO_SETTINGS_MODULE=config.settings.prod
#
# Différences clés avec base.py (développement) :
#   - DEBUG = False : Django ne montre plus les détails d'erreur (sécurité)
#   - DATABASES  : PostgreSQL réel (pas SQLite)
#   - Entêtes HTTPS : protection XSS, HSTS, HTTPS forcé
#   - Cookies sécurisés : CSRF et session transmis uniquement via HTTPS
#
# Toutes les valeurs sensibles (DB_PASSWORD, ALLOWED_HOSTS…) viennent
# du fichier .env lu par django-environ dans base.py.
# ==============================================================================

# Hérite de toute la configuration de base (apps, middleware, i18n, etc.)
from .base import *

# En production, DEBUG=False est OBLIGATOIRE pour la sécurité :
# - Django n'affiche plus les tracebacks (qui révèlent la structure du code)
# - Les fichiers statiques ne sont plus servis par Django (WhiteNoise le fait)
DEBUG = False

# Liste des noms de domaine autorisés à servir l'application.
# Lue depuis la variable d'environnement ALLOWED_HOSTS (liste séparée par virgules).
# Exemple dans .env : ALLOWED_HOSTS=healthconnect.gn,www.healthconnect.gn
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])

# Configuration PostgreSQL (remplace SQLite de base.py)
# Toutes les valeurs viennent du fichier .env (jamais en dur dans le code)
DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.postgresql',
        'NAME':     env('DB_NAME'),                    # nom de la base de données
        'USER':     env('DB_USER'),                    # utilisateur PostgreSQL
        'PASSWORD': env('DB_PASSWORD'),                # mot de passe (jamais en clair ici)
        'HOST':     env('DB_HOST', default='localhost'),
        'PORT':     env('DB_PORT', default='5432'),
    }
}

# ===========================================================================
# Entêtes de sécurité HTTP
# Ces entêtes sont envoyés avec chaque réponse pour protéger les clients.
# ===========================================================================

# Demande au navigateur d'activer son filtre XSS intégré
SECURE_BROWSER_XSS_FILTER = True

# Empêche le navigateur de "deviner" le type MIME d'une réponse
# (protection contre les attaques MIME sniffing)
SECURE_CONTENT_TYPE_NOSNIFF = True

# Empêche l'application d'être affichée dans une iframe (protection clickjacking)
X_FRAME_OPTIONS = 'DENY'

# Redirige toutes les requêtes HTTP vers HTTPS (301)
SECURE_SSL_REDIRECT = True

# Le cookie de session est transmis uniquement via HTTPS (jamais en HTTP)
SESSION_COOKIE_SECURE = True

# Le cookie CSRF est transmis uniquement via HTTPS (jamais en HTTP)
CSRF_COOKIE_SECURE = True

# HSTS (HTTP Strict Transport Security) :
# Indique au navigateur de ne jamais utiliser HTTP pour ce domaine pendant 1 an.
# Une fois ce header reçu, le navigateur refuse automatiquement les connexions HTTP.
SECURE_HSTS_SECONDS             = 31536000  # 1 an = 365 * 24 * 3600 secondes
SECURE_HSTS_INCLUDE_SUBDOMAINS  = True      # étend HSTS à tous les sous-domaines
SECURE_HSTS_PRELOAD             = True      # autorise l'inscription dans la liste HSTS preload
