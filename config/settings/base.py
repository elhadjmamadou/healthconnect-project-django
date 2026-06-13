# ==============================================================================
# config/settings/base.py — Configuration Django commune à tous les environnements
# ==============================================================================
# Ce fichier est importé par dev.py (développement) et prod.py (production).
# Il contient tous les paramètres partagés : apps installées, middleware, BDD auth,
# internationalisation, media, email, Djomy, etc.
#
# Les valeurs sensibles (SECRET_KEY, clés API) sont lues depuis un fichier .env
# grâce à la bibliothèque django-environ. Le fichier .env ne doit JAMAIS être
# commité dans git (ajouté dans .gitignore).
# ==============================================================================

from pathlib import Path
import environ

# environ.Env() : instance qui lit les variables d'environnement
env = environ.Env()

# BASE_DIR : chemin racine du projet (dossier contenant manage.py)
# __file__ = config/settings/base.py → .parent.parent.parent = racine
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Lecture du fichier .env situé à la racine du projet
environ.Env.read_env(BASE_DIR / '.env')

# Clé secrète Django : utilisée pour signer les cookies, tokens CSRF, sessions…
# DOIT être unique et secrète en production (jamais en clair dans le code)
SECRET_KEY = env('SECRET_KEY')

# ==============================================================================
# APPLICATIONS INSTALLÉES
# ==============================================================================
# Django suit une architecture modulaire : chaque fonctionnalité est une "app".
# L'ordre est important pour certaines dépendances (ex : users avant patients).
# ==============================================================================
INSTALLED_APPS = [
    # Apps Django intégrées — fournissent l'admin, l'auth, le ORM, les sessions…
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',   # nécessaire pour les relations génériques
    'django.contrib.sessions',       # sessions utilisateur (cookies)
    'django.contrib.messages',       # messages flash (success, error…)
    'django.contrib.staticfiles',    # gestion des fichiers statiques (CSS, JS)
    'django.contrib.humanize',       # filtres template : |intcomma, |naturaltime…

    # Apps tierces installées via pip
    'rest_framework',                # Django REST Framework (API REST)
    'crispy_forms',                  # rendu automatique des formulaires Bootstrap
    'crispy_bootstrap5',             # thème Bootstrap 5 pour crispy_forms
    'whitenoise.runserver_nostatic', # sert les fichiers statiques sans Nginx en dev

    # Apps locales — les 9 modules métier de HealthConnect
    'users',          # modèle User custom (authentification par email + rôles)
    'patients',       # profils patients + dossiers médicaux
    'medecins',       # profils médecins + spécialités
    'disponibilites', # créneaux de disponibilité des médecins
    'rendez_vous',    # prise et gestion des rendez-vous
    'consultations',  # comptes-rendus de consultations + ordonnances
    'paiements',      # paiement mobile money via Djomy
    'notifications',  # notifications in-app + email automatiques
    'rapports',       # dashboard admin + génération de rapports PDF
]

# ==============================================================================
# MIDDLEWARE — couche intermédiaire traitant chaque requête HTTP
# Exécutés dans l'ordre à la réception, dans l'ordre inverse à la réponse.
# ==============================================================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',          # HTTPS, HSTS…
    'whitenoise.middleware.WhiteNoiseMiddleware',             # fichiers statiques compressés
    'django.contrib.sessions.middleware.SessionMiddleware',  # gestion des sessions
    'django.middleware.common.CommonMiddleware',              # trailing slash, etc.
    'django.middleware.csrf.CsrfViewMiddleware',             # protection CSRF (formulaires)
    'django.contrib.auth.middleware.AuthenticationMiddleware', # request.user disponible
    'django.contrib.messages.middleware.MessageMiddleware',  # messages flash
    'django.middleware.clickjacking.XFrameOptionsMiddleware', # protection clickjacking
]

ROOT_URLCONF = 'config.urls'  # fichier urls.py racine du projet

# ==============================================================================
# TEMPLATES — moteur de rendu HTML (Django Template Language)
# ==============================================================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # dossier templates/ à la racine du projet
        'APP_DIRS': True,   # cherche aussi templates/ dans chaque app installée
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',   # request disponible dans les templates
                'django.contrib.auth.context_processors.auth',  # user et perms disponibles
                'django.contrib.messages.context_processors.messages',
                # Processor custom : injecte nb_notifs_non_lues dans tous les templates
                # → affiche le badge rouge sur l'icône cloche de la navbar
                'notifications.context_processors.notifications_non_lues',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ==============================================================================
# AUTHENTIFICATION PERSONNALISÉE
# ==============================================================================
# AUTH_USER_MODEL : dit à Django d'utiliser notre User custom à la place
# du User Django par défaut. DOIT être défini AVANT la première migration.
# Format : 'nom_app.NomModele'
AUTH_USER_MODEL = 'users.User'

# Règles de validation des mots de passe (actives dans les formulaires)
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ==============================================================================
# INTERNATIONALISATION
# ==============================================================================
LANGUAGE_CODE = 'fr-fr'          # langue française → admin, messages d'erreur en français
TIME_ZONE     = 'Africa/Conakry' # fuseau horaire de Conakry (GMT+0, pas de changement d'heure)
USE_I18N = True   # activer les traductions
USE_TZ   = True   # stocker les dates en UTC en base, convertir à l'affichage

# ==============================================================================
# FICHIERS STATIQUES (CSS, JavaScript, images du projet)
# ==============================================================================
STATIC_URL  = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']   # dossier source des fichiers statiques
STATIC_ROOT = BASE_DIR / 'staticfiles'     # destination après `collectstatic` (production)
# WhiteNoise : compresse et met en cache les fichiers statiques avec versioning
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ==============================================================================
# EMAIL — configuration de l'envoi d'emails
# ==============================================================================
# En développement : EMAIL_BACKEND = console → les emails s'affichent dans le terminal
# En production    : EMAIL_BACKEND = SMTP  → envoi réel via un serveur mail
EMAIL_BACKEND   = env('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='no-reply@healthconnect.local')

# ==============================================================================
# FICHIERS MEDIA (photos de profil, PDFs générés, rapports)
# ==============================================================================
MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'  # dossier de stockage sur le serveur

# ==============================================================================
# DIVERS
# ==============================================================================
# Type de clé primaire par défaut pour tous les modèles (BigAutoField = BIGINT)
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# URLs de redirection pour l'authentification
LOGIN_URL          = '/users/login/'   # redirige vers ici si LoginRequired échoue
LOGIN_REDIRECT_URL = '/dashboard/'     # après connexion réussie
LOGOUT_REDIRECT_URL = '/users/login/'  # après déconnexion

# Configuration de crispy_forms (rendu automatique des formulaires)
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# Django REST Framework — configuration de l'API REST (utilisée pour les webhooks)
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',  # auth par session Django
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# ==============================================================================
# DJOMY — Agrégateur de paiement mobile money guinéen
# Ces valeurs sont lues depuis .env pour ne jamais apparaître dans le code source
# DJOMY_API_KEY         : clé d'authentification à l'API Djomy
# DJOMY_BASE_URL        : URL de base de l'API (v1)
# DJOMY_WEBHOOK_SECRET  : secret partagé pour valider les signatures HMAC-SHA256
# ==============================================================================
DJOMY_API_KEY        = env('DJOMY_API_KEY', default='')
DJOMY_BASE_URL       = env('DJOMY_BASE_URL', default='https://api.djomy.africa/v1')
DJOMY_WEBHOOK_SECRET = env('DJOMY_WEBHOOK_SECRET', default='')
