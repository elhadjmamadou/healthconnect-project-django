# ==============================================================================
# users/urls.py — Routes de l'application users (authentification)
# ==============================================================================
# app_name = 'users' : espace de noms pour les URLs.
# Dans les templates : {% url 'users:login' %}, {% url 'users:profile' %}
#
# Routes personnalisées (vues dans users/views.py) :
#
#   login/           → LoginView : formulaire de connexion + redirection post-login
#   register/        → RegisterView : création de compte patient
#   logout/          → LogoutView : déconnexion + redirection vers la landing page
#   dashboard/       → DashboardRedirectView : redirige selon le rôle de l'utilisateur
#                      patient → /patients/dashboard/
#                      medecin → /medecins/dashboard/
#                      admin   → /rapports/dashboard/
#   profile/         → ProfileView : modification du profil (nom, téléphone, photo)
#   password-change/ → PasswordChangeView : changement de mot de passe + mise à jour session
#
# Routes de réinitialisation de mot de passe (vues Django built-in) :
# Django fournit 4 vues pour le flux complet de réinitialisation par email :
#
#   password-reset/           → 1. Saisie de l'email → envoi du lien de réinitialisation
#   password-reset/done/      → 2. Page de confirmation "email envoyé"
#   password-reset/confirm/<uidb64>/<token>/  → 3. Saisie du nouveau mot de passe
#                              <uidb64> : identifiant user encodé en base64
#                              <token>  : token à usage unique (expire après utilisation)
#   password-reset/complete/  → 4. Page de confirmation "mot de passe changé"
#
# On surcharge uniquement les template_name pour utiliser nos templates Tailwind.
# La logique d'envoi d'email et de vérification du token est gérée par Django.
# ==============================================================================

from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Authentification de base
    path('login/', views.LoginView.as_view(), name='login'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('logout/', views.LogoutView.as_view(), name='logout'),

    # Redirection intelligente selon le rôle de l'utilisateur
    path('dashboard/', views.DashboardRedirectView.as_view(), name='dashboard_redirect'),

    # Gestion du profil et du mot de passe
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('password-change/', views.PasswordChangeView.as_view(), name='password_change'),

    # Flux de réinitialisation de mot de passe (4 étapes, vues Django built-in)
    # On utilise auth_views (alias pour django.contrib.auth.views) avec nos templates
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset.html',
        email_template_name='registration/password_reset_email.html',    # corps de l'email
        subject_template_name='registration/password_reset_subject.txt', # objet de l'email
    ), name='password_reset'),

    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html',
    ), name='password_reset_done'),

    # <uidb64> : user ID encodé base64 | <token> : token à usage unique signé par Django
    path('password-reset/confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html',
    ), name='password_reset_confirm'),

    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html',
    ), name='password_reset_complete'),
]
