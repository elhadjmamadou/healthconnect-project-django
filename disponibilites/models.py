# ==============================================================================
# disponibilites/models.py — Créneaux de disponibilité des médecins
# ==============================================================================
# Un médecin publie ses créneaux de disponibilité à l'avance.
# Les patients voient ces créneaux dans l'annuaire public et les sélectionnent
# lors de la prise de rendez-vous.
#
# Cycle de vie d'un créneau :
#   LIBRE → RESERVE (quand un RDV y est associé)
#        → INDISPONIBLE (médecin bloqué ce créneau manuellement)
#        → ANNULE (créneau supprimé)
# ==============================================================================

from django.core.exceptions import ValidationError
from django.db import models


class Disponibilite(models.Model):
    """
    Créneau de disponibilité publié par un médecin.

    Un créneau a une date, une heure de début et une heure de fin.
    La validation (méthode clean) interdit les chevauchements pour le
    même médecin à la même date — même logique que RendezVous.clean().

    La relation OneToOneField avec RendezVous (définie côté RendezVous,
    related_name='rendez_vous') permet de savoir si un créneau est déjà pris.
    """

    # Statut du créneau — mis à jour automatiquement lors de la réservation
    class StatutCreneau(models.TextChoices):
        LIBRE        = 'libre',        'Libre'
        RESERVE      = 'reserve',      'Réservé'
        INDISPONIBLE = 'indisponible', 'Indisponible'
        ANNULE       = 'annule',       'Annulé'

    # Type de consultation possible sur ce créneau
    class TypeCreneau(models.TextChoices):
        PRESENTIEL      = 'presentiel',      'Présentiel'
        TELECONSULTATION = 'teleconsultation', 'Téléconsultation'
        LES_DEUX        = 'les_deux',        'Présentiel & Téléconsultation'

    # ForeignKey : un médecin peut avoir PLUSIEURS créneaux
    medecin = models.ForeignKey(
        'medecins.Medecin',
        on_delete=models.CASCADE,   # CASCADE : si le médecin est supprimé, ses créneaux aussi
        related_name='disponibilites',
        verbose_name='Médecin',
    )

    date_disponibilite = models.DateField(verbose_name='Date')
    heure_debut        = models.TimeField(verbose_name='Heure de début')
    heure_fin          = models.TimeField(verbose_name='Heure de fin')

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

    date_creation    = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    date_modification = models.DateTimeField(auto_now=True, verbose_name='Dernière modification')

    class Meta:
        verbose_name = 'Disponibilité'
        verbose_name_plural = 'Disponibilités'
        ordering = ['date_disponibilite', 'heure_debut']  # tri chronologique
        indexes = [
            # Index composé pour la requête la plus fréquente : "créneaux libres d'un médecin à une date"
            # Utilisé par AnnuaireDetailView pour afficher les prochaines disponibilités
            models.Index(fields=['medecin', 'date_disponibilite', 'statut_creneau']),
        ]

    def __str__(self):
        return (
            f'{self.medecin} — {self.date_disponibilite} '
            f'{self.heure_debut:%H:%M}-{self.heure_fin:%H:%M}'
        )

    def clean(self):
        """
        Validation métier : empêcher les créneaux incohérents ou qui se chevauchent.

        Deux règles :
          1. L'heure de début doit être strictement antérieure à l'heure de fin
          2. Pas de chevauchement avec un autre créneau du même médecin à la même date

        Même algorithme de détection de chevauchement que RendezVous.clean() :
          chevauchement si heure_debut_existant < heure_fin_nouveau
                       ET heure_fin_existant > heure_debut_nouveau
        """
        if self.heure_debut and self.heure_fin:
            if self.heure_debut >= self.heure_fin:
                raise ValidationError("L'heure de début doit être antérieure à l'heure de fin.")

            chevauchements = Disponibilite.objects.filter(
                medecin=self.medecin,
                date_disponibilite=self.date_disponibilite,
                heure_debut__lt=self.heure_fin,
                heure_fin__gt=self.heure_debut,
            )
            # Exclure le créneau lui-même lors d'une modification
            if self.pk:
                chevauchements = chevauchements.exclude(pk=self.pk)
            if chevauchements.exists():
                raise ValidationError(
                    "Ce créneau chevauche une disponibilité existante pour ce médecin."
                )

    # ------------------------------------------------------------------
    # Propriétés utilitaires
    # ------------------------------------------------------------------

    @property
    def est_libre(self):
        """Vrai si le créneau est disponible à la réservation."""
        return self.statut_creneau == self.StatutCreneau.LIBRE

    @property
    def duree_minutes(self):
        """
        Calcule la durée du créneau en minutes.

        datetime.combine() assemble une date et une heure en datetime complet
        pour pouvoir faire la soustraction et obtenir un timedelta.
        total_seconds() / 60 convertit en minutes entières.
        """
        from datetime import datetime, date
        debut = datetime.combine(date.today(), self.heure_debut)
        fin   = datetime.combine(date.today(), self.heure_fin)
        return int((fin - debut).total_seconds() / 60)
