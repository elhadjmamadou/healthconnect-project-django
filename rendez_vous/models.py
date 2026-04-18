from django.core.exceptions import ValidationError
from django.db import models


class RendezVous(models.Model):

    class StatutRdv(models.TextChoices):
        EN_ATTENTE = 'en_attente', 'En attente'
        CONFIRME = 'confirme', 'Confirmé'
        ANNULE_PATIENT = 'annule_patient', 'Annulé par le patient'
        ANNULE_MEDECIN = 'annule_medecin', 'Annulé par le médecin'
        TERMINE = 'termine', 'Terminé'
        NO_SHOW = 'no_show', 'Non présenté'

    class Canal(models.TextChoices):
        PLATEFORME = 'plateforme', 'Plateforme'
        TELEPHONE = 'telephone', 'Téléphone'
        DIRECT = 'direct', 'Direct'

    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='rendez_vous',
        verbose_name='Patient',
    )
    medecin = models.ForeignKey(
        'medecins.Medecin',
        on_delete=models.CASCADE,
        related_name='rendez_vous',
        verbose_name='Médecin',
    )
    disponibilite = models.OneToOneField(
        'disponibilites.Disponibilite',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rendez_vous',
        verbose_name='Créneau',
    )
    date_rdv = models.DateField(verbose_name='Date du rendez-vous')
    heure_debut = models.TimeField(verbose_name='Heure de début')
    heure_fin = models.TimeField(verbose_name='Heure de fin')
    statut_rdv = models.CharField(
        max_length=20,
        choices=StatutRdv.choices,
        default=StatutRdv.EN_ATTENTE,
        verbose_name='Statut',
    )
    motif = models.TextField(blank=True, verbose_name='Motif de la consultation')
    canal = models.CharField(
        max_length=15,
        choices=Canal.choices,
        default=Canal.PLATEFORME,
        verbose_name='Canal de prise de rendez-vous',
    )
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    date_modification = models.DateTimeField(auto_now=True, verbose_name='Dernière modification')

    class Meta:
        verbose_name = 'Rendez-vous'
        verbose_name_plural = 'Rendez-vous'
        ordering = ['-date_rdv', '-heure_debut']
        indexes = [
            models.Index(fields=['medecin', 'date_rdv', 'statut_rdv']),
            models.Index(fields=['patient', 'date_rdv']),
        ]

    def __str__(self):
        return (
            f'RDV {self.patient} — {self.medecin} '
            f'le {self.date_rdv} à {self.heure_debut:%H:%M}'
        )

    def clean(self):
        statuts_actifs = [self.StatutRdv.EN_ATTENTE, self.StatutRdv.CONFIRME]
        if self.statut_rdv in statuts_actifs and self.medecin_id and self.date_rdv:
            chevauchements = RendezVous.objects.filter(
                medecin=self.medecin,
                date_rdv=self.date_rdv,
                statut_rdv__in=statuts_actifs,
                heure_debut__lt=self.heure_fin,
                heure_fin__gt=self.heure_debut,
            )
            if self.pk:
                chevauchements = chevauchements.exclude(pk=self.pk)
            if chevauchements.exists():
                raise ValidationError(
                    "Ce médecin a déjà un rendez-vous sur ce créneau."
                )

    @property
    def est_annulable(self):
        return self.statut_rdv in [self.StatutRdv.EN_ATTENTE, self.StatutRdv.CONFIRME]

    @property
    def est_actif(self):
        return self.statut_rdv in [self.StatutRdv.EN_ATTENTE, self.StatutRdv.CONFIRME]
