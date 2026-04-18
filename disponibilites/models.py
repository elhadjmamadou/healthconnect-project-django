from django.core.exceptions import ValidationError
from django.db import models


class Disponibilite(models.Model):

    class StatutCreneau(models.TextChoices):
        LIBRE = 'libre', 'Libre'
        RESERVE = 'reserve', 'Réservé'
        INDISPONIBLE = 'indisponible', 'Indisponible'
        ANNULE = 'annule', 'Annulé'

    class TypeCreneau(models.TextChoices):
        PRESENTIEL = 'presentiel', 'Présentiel'
        TELECONSULTATION = 'teleconsultation', 'Téléconsultation'
        LES_DEUX = 'les_deux', 'Présentiel & Téléconsultation'

    medecin = models.ForeignKey(
        'medecins.Medecin',
        on_delete=models.CASCADE,
        related_name='disponibilites',
        verbose_name='Médecin',
    )
    date_disponibilite = models.DateField(verbose_name='Date')
    heure_debut = models.TimeField(verbose_name='Heure de début')
    heure_fin = models.TimeField(verbose_name='Heure de fin')
    statut_creneau = models.CharField(
        max_length=15,
        choices=StatutCreneau.choices,
        default=StatutCreneau.LIBRE,
        verbose_name='Statut du créneau',
    )
    type_creneau = models.CharField(
        max_length=20,
        choices=TypeCreneau.choices,
        default=TypeCreneau.PRESENTIEL,
        verbose_name='Type de créneau',
    )
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    date_modification = models.DateTimeField(auto_now=True, verbose_name='Dernière modification')

    class Meta:
        verbose_name = 'Disponibilité'
        verbose_name_plural = 'Disponibilités'
        ordering = ['date_disponibilite', 'heure_debut']
        indexes = [
            models.Index(fields=['medecin', 'date_disponibilite', 'statut_creneau']),
        ]

    def __str__(self):
        return (
            f'{self.medecin} — {self.date_disponibilite} '
            f'{self.heure_debut:%H:%M}-{self.heure_fin:%H:%M}'
        )

    def clean(self):
        if self.heure_debut and self.heure_fin:
            if self.heure_debut >= self.heure_fin:
                raise ValidationError("L'heure de début doit être antérieure à l'heure de fin.")

            # Vérification de chevauchement pour le même médecin à la même date
            chevauchements = Disponibilite.objects.filter(
                medecin=self.medecin,
                date_disponibilite=self.date_disponibilite,
                heure_debut__lt=self.heure_fin,
                heure_fin__gt=self.heure_debut,
            )
            if self.pk:
                chevauchements = chevauchements.exclude(pk=self.pk)
            if chevauchements.exists():
                raise ValidationError(
                    "Ce créneau chevauche une disponibilité existante pour ce médecin."
                )

    @property
    def est_libre(self):
        return self.statut_creneau == self.StatutCreneau.LIBRE

    @property
    def duree_minutes(self):
        from datetime import datetime, date
        debut = datetime.combine(date.today(), self.heure_debut)
        fin = datetime.combine(date.today(), self.heure_fin)
        return int((fin - debut).total_seconds() / 60)
