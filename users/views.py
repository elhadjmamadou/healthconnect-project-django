# ==============================================================================
# users/views.py — Authentification, inscription et gestion du profil
# ==============================================================================
# Ce fichier contient les vues liées à l'identité de l'utilisateur :
#
# LandingView         : page d'accueil publique avec stats réelles de la plateforme
# LoginView           : connexion par email + mot de passe
# RegisterView        : inscription (rôle patient par défaut)
# LogoutView          : déconnexion (POST only pour éviter la déconnexion par lien)
# DashboardRedirectView : aiguillage vers le bon dashboard selon le rôle
# ProfileView         : modification du profil (photo, téléphone…)
# PasswordChangeView  : changement de mot de passe avec session mise à jour
# ==============================================================================

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views import View

from .forms import LoginForm, ProfileForm, RegisterForm
from .models import User


class LandingView(View):
    """
    Page d'accueil publique de HealthConnect.

    Si l'utilisateur est déjà connecté → redirection immédiate vers son dashboard
    (pas besoin de revoir la landing page).

    Si l'utilisateur n'est pas connecté → affichage de la landing avec :
      - Liste des spécialités médicales (pour la marquee animée)
      - Stats réelles de la plateforme (nb médecins, patients, spécialités, RDV)

    Ces données sont calculées en temps réel depuis la base de données pour
    que la landing page reste toujours à jour automatiquement.
    """

    template_name = 'landing.html'

    def get(self, request):
        # Utilisateur connecté → on l'envoie directement vers son espace
        if request.user.is_authenticated:
            return redirect('users:dashboard_redirect')

        # Import locaux pour éviter les imports circulaires au niveau module
        # (users dépend de medecins/patients/rendez_vous qui dépendent de users)
        from medecins.models import Medecin, Specialite
        from patients.models import Patient
        from rendez_vous.models import RendezVous

        return render(request, self.template_name, {
            # Toutes les spécialités pour la marquee défilante de la landing
            'specialites': Specialite.objects.order_by('libelle'),
            # Stats affichées dans la section "Chiffres clés" de la landing
            'stats': {
                'medecins':    Medecin.objects.count(),
                'specialites': Specialite.objects.count(),
                'patients':    Patient.objects.count(),
                'rendez_vous': RendezVous.objects.count(),
            },
        })


class LoginView(View):
    """
    Page de connexion par email et mot de passe.

    Django ne gère pas nativement la connexion par email — il utilise
    le champ USERNAME_FIELD. On a configuré USERNAME_FIELD = 'email' dans
    User, donc authenticate() accepte l'email comme "username".

    Gestion du paramètre ?next= :
      Si l'utilisateur était redirigé vers la page de login depuis une page
      protégée (LoginRequiredMixin), Django ajoute ?next=/chemin/original.
      Après connexion réussie, on redirige vers ce chemin pour ne pas perdre
      la navigation de l'utilisateur.
    """

    template_name = 'users/login.html'

    def get(self, request):
        # Utilisateur déjà connecté → pas besoin de la page login
        if request.user.is_authenticated:
            return redirect('users:dashboard_redirect')
        return render(request, self.template_name, {'form': LoginForm()})

    def post(self, request):
        form = LoginForm(request.POST)
        if form.is_valid():
            email    = form.cleaned_data['username']   # le champ s'appelle 'username' dans le form
            password = form.cleaned_data['password']

            # authenticate() vérifie email + mot de passe hashé en base
            # Retourne l'objet User si valide, None sinon
            user = authenticate(request, username=email, password=password)

            if user is not None:
                # login() crée la session Django et définit le cookie de session
                login(request, user)

                # Redirection vers la page d'origine si elle existe (?next=...)
                next_url = request.GET.get('next', '')
                if next_url:
                    return redirect(next_url)
                return redirect('users:dashboard_redirect')
            else:
                # add_error(None, ...) : erreur globale (pas liée à un champ)
                form.add_error(None, 'Email ou mot de passe incorrect.')

        return render(request, self.template_name, {'form': form})


class RegisterView(View):
    """
    Inscription d'un nouvel utilisateur (rôle patient par défaut).

    RegisterForm crée un User avec role='patient' automatiquement.
    Après inscription réussie :
      1. L'utilisateur est connecté immédiatement (login())
      2. Un signal post_save crée automatiquement le profil Patient
         et le DossierMedical associé (patients/signals.py)
      3. Redirection vers le dashboard patient
    """

    template_name = 'users/register.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('users:dashboard_redirect')
        return render(request, self.template_name, {'form': RegisterForm()})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()  # crée le User + hash le mot de passe

            # Connexion immédiate après inscription (UX fluide, pas besoin de re-login)
            login(request, user)
            messages.success(request, f'Bienvenue sur HealthConnect, {user.first_name} !')
            return redirect('users:dashboard_redirect')

        return render(request, self.template_name, {'form': form})


class LogoutView(View):
    """
    Déconnexion de l'utilisateur.

    On n'accepte que POST (pas GET) pour éviter qu'un lien malveillant
    puisse déconnecter l'utilisateur à son insu (CSRF protection).
    logout() supprime la session côté serveur et efface le cookie.
    """

    def post(self, request):
        logout(request)
        return redirect('users:login')


@method_decorator(login_required, name='dispatch')
class DashboardRedirectView(View):
    """
    Aiguillage vers le dashboard approprié selon le rôle de l'utilisateur.

    Appelé après connexion et après inscription.
    @method_decorator(login_required) : équivalent de LoginRequiredMixin
    mais en décorateur Python (syntaxe alternative pour les CBV).

    Routing des dashboards :
      Admin/Staff → /rapports/dashboard/  (vue DashboardAdminView)
      Médecin     → /medecins/dashboard/  (vue DashboardMedecinView)
      Patient     → /patients/dashboard/  (vue DashboardPatientView)
    """

    def get(self, request):
        user = request.user
        if user.is_admin_role or user.is_staff:
            return redirect('rapports:dashboard_admin')
        elif user.is_medecin:
            return redirect('medecins:dashboard')
        else:
            return redirect('patients:dashboard')


@method_decorator(login_required, name='dispatch')
class ProfileView(View):
    """
    Affichage et modification du profil de l'utilisateur connecté.

    GET  → affiche le formulaire pré-rempli avec les données actuelles
    POST → valide et sauvegarde les modifications (photo, téléphone, prénom, nom)

    request.FILES est nécessaire pour gérer l'upload de la photo de profil
    (les fichiers ne sont pas dans request.POST).
    instance=request.user : le formulaire travaille sur l'objet User existant
    (UPDATE SQL), pas sur un nouvel objet (INSERT SQL).
    """

    template_name = 'users/profile.html'

    def get(self, request):
        form = ProfileForm(instance=request.user)
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        # request.FILES contient les fichiers uploadés (photo de profil)
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil mis à jour avec succès.')
            return redirect('users:profile')
        return render(request, self.template_name, {'form': form})


@method_decorator(login_required, name='dispatch')
class PasswordChangeView(View):
    """
    Changement de mot de passe pour l'utilisateur connecté.

    PasswordChangeForm (Django built-in) :
      - Vérifie l'ancien mot de passe (sécurité)
      - Vérifie que le nouveau mot de passe est confirmé
      - Hache le nouveau mot de passe avant sauvegarde

    update_session_auth_hash() : CRUCIAL — Django invalide la session après
    un changement de mot de passe pour des raisons de sécurité. Sans cet appel,
    l'utilisateur serait automatiquement déconnecté après le changement.
    update_session_auth_hash() met à jour le hash dans la session actuelle
    pour maintenir l'utilisateur connecté.
    """

    template_name = 'users/password_change.html'

    def get(self, request):
        form = PasswordChangeForm(request.user)  # premier arg = user courant
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()  # sauvegarde le nouveau mot de passe hashé

            # Maintenir la session active après changement de mot de passe
            # Sans cela, Django déconnecte l'utilisateur pour des raisons de sécurité
            update_session_auth_hash(request, user)
            messages.success(request, 'Mot de passe modifié avec succès.')
            return redirect('users:profile')

        return render(request, self.template_name, {'form': form})
