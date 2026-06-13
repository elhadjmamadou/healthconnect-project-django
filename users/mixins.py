# ==============================================================================
# users/mixins.py — Contrôle d'accès par rôle pour les vues basées sur des classes
# ==============================================================================
# Django propose LoginRequiredMixin (vérifie qu'on est connecté) et
# UserPassesTestMixin (vérifie une condition arbitraire). On combine les deux
# pour créer trois "gardes" réutilisables : une par rôle métier.
#
# Utilisation dans une vue :
#   class MaVue(PatientRequiredMixin, View):
#       ...
# Si l'utilisateur n'est pas connecté → redirection vers la page de login.
# Si l'utilisateur est connecté mais n'a pas le bon rôle → erreur 403.
# ==============================================================================

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect


class PatientRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Restreint l'accès aux utilisateurs dont le rôle est PATIENT.

    Héritage multiple (MRO Python) :
      1. LoginRequiredMixin  → vérifie d'abord que l'utilisateur est connecté
      2. UserPassesTestMixin → appelle test_func() pour vérifier le rôle
    """

    def test_func(self):
        # is_patient est une @property définie sur User (users/models.py)
        # Elle retourne True uniquement si self.role == 'patient'
        return self.request.user.is_patient


class MedecinRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Restreint l'accès aux utilisateurs dont le rôle est MEDECIN.

    Exemple d'usage : RedigerOrdonnanceView ne doit être accessible
    qu'aux médecins — un patient ne doit pas pouvoir créer une ordonnance.
    """

    def test_func(self):
        return self.request.user.is_medecin


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Restreint l'accès aux administrateurs de la plateforme.

    On accepte DEUX types d'administrateurs :
      - is_admin_role : rôle applicatif défini dans notre modèle User
      - is_staff      : super-utilisateur Django (créé via createsuperuser)
    Cela permet à un compte "staff" de gérer la plateforme même sans
    se voir attribuer explicitement le rôle 'admin' dans l'app.
    """

    def test_func(self):
        return self.request.user.is_admin_role or self.request.user.is_staff
