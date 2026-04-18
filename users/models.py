from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    class Role(models.TextChoices):
        PATIENT = 'patient', 'Patient'
        MEDECIN = 'medecin', 'Médecin'
        ADMIN = 'admin', 'Administrateur'

    class Statut(models.TextChoices):
        ACTIF = 'actif', 'Actif'
        INACTIF = 'inactif', 'Inactif'
        SUSPENDU = 'suspendu', 'Suspendu'

    email = models.EmailField(unique=True, verbose_name='Adresse email')
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.PATIENT,
        verbose_name='Rôle',
    )
    telephone = models.CharField(max_length=20, blank=True, verbose_name='Téléphone')
    photo = models.ImageField(
        upload_to='users/photos/',
        null=True,
        blank=True,
        verbose_name='Photo de profil',
    )
    statut = models.CharField(
        max_length=10,
        choices=Statut.choices,
        default=Statut.ACTIF,
        verbose_name='Statut',
    )
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    date_modification = models.DateTimeField(auto_now=True, verbose_name='Dernière modification')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'
        ordering = ['-date_creation']

    def __str__(self):
        return f'{self.get_full_name()} ({self.email})'

    @property
    def is_patient(self):
        return self.role == self.Role.PATIENT

    @property
    def is_medecin(self):
        return self.role == self.Role.MEDECIN

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN
