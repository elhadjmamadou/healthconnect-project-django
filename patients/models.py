# ==============================================================================
# patients/models.py — Profil médical du patient
# ==============================================================================
# Le modèle Patient complète le modèle User avec les données de santé.
# Séparation des responsabilités :
#   User    → données d'identité et d'authentification (email, mot de passe)
#   Patient → données médicales (groupe sanguin, allergies, antécédents…)
#
# Cette séparation suit le principe de responsabilité unique (SRP) et
# facilite la gestion des droits d'accès (un médecin peut voir Patient
# sans forcément voir les données d'authentification de User).
# ==============================================================================

from datetime import date

from django.db import models
from django.utils import timezone


class Patient(models.Model):
    """
    Profil médical associé à un utilisateur Patient.

    Créé automatiquement lors de l'inscription d'un utilisateur avec le
    rôle PATIENT (via un signal post_save dans users/signals.py ou patients/signals.py).

    related_name='patient_profile' permet d'écrire :
      request.user.patient_profile.groupe_sanguin
    depuis n'importe quelle vue.
    """

    # Sexe biologique — utilisé pour certains calculs médicaux (ex : dosage)
    class Sexe(models.TextChoices):
        MASCULIN = 'M',      'Masculin'
        FEMININ  = 'F',      'Féminin'
        AUTRE    = 'autre',  'Autre'

    # Groupe sanguin ABO + Rhésus — crucial en cas d'urgence médicale
    class GroupeSanguin(models.TextChoices):
        A_POS  = 'A+',  'A+'
        A_NEG  = 'A-',  'A-'
        B_POS  = 'B+',  'B+'
        B_NEG  = 'B-',  'B-'
        AB_POS = 'AB+', 'AB+'
        AB_NEG = 'AB-', 'AB-'
        O_POS  = 'O+',  'O+'
        O_NEG  = 'O-',  'O-'

    # OneToOneField : 1 patient = 1 compte User (et inversement)
    # CASCADE : supprimer le User supprime le Patient
    # related_name : user.patient_profile donne accès au Patient depuis le User
    user = models.OneToOneField(
        'users.User',
        on_delete=models.CASCADE,
        related_name='patient_profile',
        verbose_name='Utilisateur',
    )

    # Données médicales — toutes optionnelles (null/blank=True) car
    # le patient peut les renseigner progressivement dans son profil
    date_naissance = models.DateField(null=True, blank=True, verbose_name='Date de naissance')
    sexe = models.CharField(
        max_length=5,
        choices=Sexe.choices,
        blank=True,
        verbose_name='Sexe',
    )
    adresse = models.TextField(blank=True, verbose_name='Adresse')
    groupe_sanguin = models.CharField(
        max_length=3,
        choices=GroupeSanguin.choices,
        blank=True,
        verbose_name='Groupe sanguin',
    )
    allergies = models.TextField(blank=True, verbose_name='Allergies connues')
    antecedents_resumes = models.TextField(blank=True, verbose_name='Antécédents médicaux')

    date_creation    = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    date_modification = models.DateTimeField(auto_now=True, verbose_name='Dernière modification')

    class Meta:
        verbose_name = 'Patient'
        verbose_name_plural = 'Patients'
        ordering = ['user__last_name', 'user__first_name']  # tri alphabétique

    def __str__(self):
        return self.nom_complet

    # ------------------------------------------------------------------
    # Propriétés calculées — pas de colonne supplémentaire en base de données
    # ------------------------------------------------------------------

    @property
    def nom_complet(self):
        """Nom complet depuis le User, avec fallback sur l'email."""
        return self.user.get_full_name() or self.user.email

    @property
    def age(self):
        """
        Calcule l'âge exact du patient en années.

        La soustraction (born.month, born.day) < (today.month, today.day)
        retourne True (=1) si l'anniversaire n'est pas encore passé cette
        année → on retire 1 an pour ne pas compter une année entière.

        Retourne None si la date de naissance n'est pas renseignée.
        """
        if not self.date_naissance:
            return None
        today = date.today()
        born  = self.date_naissance
        # Formule standard de calcul d'âge : on ajuste si l'anniversaire n'est pas passé
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
