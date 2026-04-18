from datetime import date

from django.db import models
from django.utils import timezone


class Patient(models.Model):

    class Sexe(models.TextChoices):
        MASCULIN = 'M', 'Masculin'
        FEMININ = 'F', 'Féminin'
        AUTRE = 'autre', 'Autre'

    class GroupeSanguin(models.TextChoices):
        A_POS = 'A+', 'A+'
        A_NEG = 'A-', 'A-'
        B_POS = 'B+', 'B+'
        B_NEG = 'B-', 'B-'
        AB_POS = 'AB+', 'AB+'
        AB_NEG = 'AB-', 'AB-'
        O_POS = 'O+', 'O+'
        O_NEG = 'O-', 'O-'

    user = models.OneToOneField(
        'users.User',
        on_delete=models.CASCADE,
        related_name='patient_profile',
        verbose_name='Utilisateur',
    )
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
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    date_modification = models.DateTimeField(auto_now=True, verbose_name='Dernière modification')

    class Meta:
        verbose_name = 'Patient'
        verbose_name_plural = 'Patients'
        ordering = ['user__last_name', 'user__first_name']

    def __str__(self):
        return self.nom_complet

    @property
    def nom_complet(self):
        return self.user.get_full_name() or self.user.email

    @property
    def age(self):
        if not self.date_naissance:
            return None
        today = date.today()
        born = self.date_naissance
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
