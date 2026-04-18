import uuid

from django.db import models


class DossierMedical(models.Model):

    class StatutDossier(models.TextChoices):
        ACTIF = 'actif', 'Actif'
        ARCHIVE = 'archive', 'Archivé'
        SUSPENDU = 'suspendu', 'Suspendu'

    patient = models.OneToOneField(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='dossier_medical',
        verbose_name='Patient',
    )
    numero_dossier = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Numéro de dossier',
    )
    date_ouverture = models.DateField(auto_now_add=True, verbose_name="Date d'ouverture")
    statut_dossier = models.CharField(
        max_length=10,
        choices=StatutDossier.choices,
        default=StatutDossier.ACTIF,
        verbose_name='Statut',
    )
    notes_generales = models.TextField(blank=True, verbose_name='Notes générales')
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    date_modification = models.DateTimeField(auto_now=True, verbose_name='Dernière modification')

    class Meta:
        verbose_name = 'Dossier médical'
        verbose_name_plural = 'Dossiers médicaux'
        ordering = ['-date_ouverture']

    def __str__(self):
        return f'Dossier {self.numero_dossier} — {self.patient}'

    def save(self, *args, **kwargs):
        if not self.numero_dossier:
            self.numero_dossier = 'HC-' + uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)

    @property
    def nombre_consultations(self):
        return self.consultations.count()


class Consultation(models.Model):
    dossier = models.ForeignKey(
        DossierMedical,
        on_delete=models.CASCADE,
        related_name='consultations',
        verbose_name='Dossier médical',
    )
    medecin = models.ForeignKey(
        'medecins.Medecin',
        on_delete=models.SET_NULL,
        null=True,
        related_name='consultations',
        verbose_name='Médecin',
    )
    rendez_vous = models.OneToOneField(
        'rendez_vous.RendezVous',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='consultation',
        verbose_name='Rendez-vous',
    )
    date_consultation = models.DateTimeField(verbose_name='Date et heure de la consultation')
    compte_rendu = models.TextField(blank=True, verbose_name='Compte rendu')
    diagnostic = models.TextField(blank=True, verbose_name='Diagnostic')
    prescription = models.TextField(blank=True, verbose_name='Prescription')
    observations = models.TextField(blank=True, verbose_name='Observations')
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    date_modification = models.DateTimeField(auto_now=True, verbose_name='Dernière modification')

    class Meta:
        verbose_name = 'Consultation'
        verbose_name_plural = 'Consultations'
        ordering = ['-date_consultation']

    def __str__(self):
        return f'Consultation {self.dossier.patient} — {self.date_consultation:%d/%m/%Y %H:%M}'
