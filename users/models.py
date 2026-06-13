# ==============================================================================
# users/models.py — Modèle utilisateur personnalisé de HealthConnect
# ==============================================================================
# Django fournit un modèle User de base (AbstractUser). Ici, on l'étend pour
# ajouter les champs propres à la plateforme (rôle, téléphone, photo, statut)
# et on configure l'authentification par e-mail plutôt que par nom d'utilisateur.
# ==============================================================================

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Utilisateur central de HealthConnect.

    Hérite de AbstractUser (mot de passe hashé, groupes, permissions, etc.)
    et y ajoute :
      - un rôle (patient / médecin / administrateur)
      - un numéro de téléphone (pour le paiement mobile money Djomy)
      - une photo de profil
      - un statut de compte (actif, inactif, suspendu)

    L'e-mail remplace le nom d'utilisateur comme identifiant de connexion.
    """

    # ------------------------------------------------------------------
    # Choix de rôle — TextChoices crée à la fois les constantes Python
    # et les libellés affichés dans l'admin et les formulaires.
    # ------------------------------------------------------------------
    class Role(models.TextChoices):
        PATIENT = 'patient', 'Patient'       # peut prendre des RDV et payer
        MEDECIN = 'medecin', 'Médecin'       # gère son agenda et ses consultations
        ADMIN = 'admin', 'Administrateur'    # accès complet au dashboard rapports

    # ------------------------------------------------------------------
    # Statut du compte — permet de suspendre un compte sans le supprimer
    # ------------------------------------------------------------------
    class Statut(models.TextChoices):
        ACTIF = 'actif', 'Actif'
        INACTIF = 'inactif', 'Inactif'
        SUSPENDU = 'suspendu', 'Suspendu'

    # L'email est rendu UNIQUE pour servir d'identifiant de connexion
    email = models.EmailField(unique=True, verbose_name='Adresse email')

    # Rôle : détermine les permissions et les pages accessibles
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.PATIENT,   # tout nouvel inscrit est patient par défaut
        verbose_name='Rôle',
    )

    # Téléphone au format guinéen (ex : +224 622 00 00 00) — requis pour Djomy
    telephone = models.CharField(max_length=20, blank=True, verbose_name='Téléphone')

    # Photo stockée dans MEDIA_ROOT/users/photos/
    photo = models.ImageField(
        upload_to='users/photos/',
        null=True,
        blank=True,
        verbose_name='Photo de profil',
    )

    # Statut du compte — "inactif" cache le médecin de l'annuaire public
    statut = models.CharField(
        max_length=10,
        choices=Statut.choices,
        default=Statut.ACTIF,
        verbose_name='Statut',
    )

    # Horodatages automatiques — auto_now_add = à la création, auto_now = à chaque save
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    date_modification = models.DateTimeField(auto_now=True, verbose_name='Dernière modification')

    # ------------------------------------------------------------------
    # Authentification par e-mail
    # USERNAME_FIELD = 'email' dit à Django d'utiliser l'e-mail pour la connexion
    # REQUIRED_FIELDS liste les champs obligatoires en plus de USERNAME_FIELD
    # lors de la commande "createsuperuser" (username reste car hérité d'AbstractUser)
    # ------------------------------------------------------------------
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'
        ordering = ['-date_creation']  # les plus récents en premier dans l'admin

    def __str__(self):
        # Représentation lisible : "Mamadou Diallo (m.diallo@example.com)"
        return f'{self.get_full_name()} ({self.email})'

    # ------------------------------------------------------------------
    # Propriétés de rôle — utilisées dans les templates ({% if request.user.is_patient %})
    # et dans les mixins de contrôle d'accès (users/mixins.py).
    # Les @property sont des attributs calculés : pas de colonne en base.
    # ------------------------------------------------------------------

    @property
    def is_patient(self):
        """Vrai si l'utilisateur est un patient."""
        return self.role == self.Role.PATIENT

    @property
    def is_medecin(self):
        """Vrai si l'utilisateur est un médecin."""
        return self.role == self.Role.MEDECIN

    @property
    def is_admin_role(self):
        """Vrai si l'utilisateur est administrateur (rôle applicatif, pas is_staff Django)."""
        return self.role == self.Role.ADMIN
