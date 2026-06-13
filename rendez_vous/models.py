# ==============================================================================
# rendez_vous/models.py — Modèle central de gestion des rendez-vous
# ==============================================================================
# Un RendezVous relie un patient, un médecin et optionnellement un créneau
# de disponibilité. Il suit un cycle de vie via des statuts (TextChoices)
# et contient une validation métier pour éviter les chevauchements.
# ==============================================================================

from django.core.exceptions import ValidationError
from django.db import models


class RendezVous(models.Model):
    """
    Représente une demande de consultation entre un patient et un médecin.

    Cycle de vie d'un RDV :
      EN_ATTENTE → CONFIRME → TERMINE
                            ↘ ANNULE_PATIENT / ANNULE_MEDECIN / NO_SHOW
    """

    # ------------------------------------------------------------------
    # Statuts — chaque valeur a une signification métier précise
    # ------------------------------------------------------------------
    class StatutRdv(models.TextChoices):
        EN_ATTENTE    = 'en_attente',    'En attente'              # créé, pas encore accepté
        CONFIRME      = 'confirme',      'Confirmé'                # le médecin a accepté
        ANNULE_PATIENT = 'annule_patient', 'Annulé par le patient' # annulé côté patient
        ANNULE_MEDECIN = 'annule_medecin', 'Annulé par le médecin' # annulé côté médecin
        TERMINE       = 'termine',       'Terminé'                 # consultation effectuée
        NO_SHOW       = 'no_show',       'Non présenté'            # patient absent

    # ------------------------------------------------------------------
    # Canal de prise de RDV — trace l'origine de la réservation
    # ------------------------------------------------------------------
    class Canal(models.TextChoices):
        PLATEFORME = 'plateforme', 'Plateforme'  # réservé via le site web
        TELEPHONE  = 'telephone',  'Téléphone'   # réservé par téléphone (secrétariat)
        DIRECT     = 'direct',     'Direct'      # walk-in (sans rendez-vous)

    # ------------------------------------------------------------------
    # Relations vers les autres apps (ForeignKey = clé étrangère en BDD)
    # on_delete=CASCADE : si le patient est supprimé, ses RDV le sont aussi
    # related_name : permet d'écrire patient.rendez_vous.all() depuis un Patient
    # ------------------------------------------------------------------
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

    # Créneau de disponibilité pré-publié par le médecin (optionnel)
    # OneToOneField garantit qu'un créneau ne peut être associé qu'à UN seul RDV
    # SET_NULL : si le créneau est supprimé, le RDV reste mais perd le lien
    disponibilite = models.OneToOneField(
        'disponibilites.Disponibilite',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rendez_vous',
        verbose_name='Créneau',
    )

    # Date et horaires du RDV — séparés pour faciliter les comparaisons de chevauchement
    date_rdv   = models.DateField(verbose_name='Date du rendez-vous')
    heure_debut = models.TimeField(verbose_name='Heure de début')
    heure_fin   = models.TimeField(verbose_name='Heure de fin')

    statut_rdv = models.CharField(
        max_length=20,
        choices=StatutRdv.choices,
        default=StatutRdv.EN_ATTENTE,
        verbose_name='Statut',
    )

    # Motif saisi par le patient lors de la réservation
    motif = models.TextField(blank=True, verbose_name='Motif de la consultation')

    canal = models.CharField(
        max_length=15,
        choices=Canal.choices,
        default=Canal.PLATEFORME,
        verbose_name='Canal de prise de rendez-vous',
    )

    date_creation    = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    date_modification = models.DateTimeField(auto_now=True, verbose_name='Dernière modification')

    class Meta:
        verbose_name = 'Rendez-vous'
        verbose_name_plural = 'Rendez-vous'
        ordering = ['-date_rdv', '-heure_debut']   # tri chronologique inversé
        indexes = [
            # Index composé pour accélérer la requête "RDV d'un médecin à une date"
            # (utilisée très souvent pour l'agenda et le contrôle de chevauchement)
            models.Index(fields=['medecin', 'date_rdv', 'statut_rdv']),
            # Index pour le calendrier patient
            models.Index(fields=['patient', 'date_rdv']),
        ]

    def __str__(self):
        return (
            f'RDV {self.patient} — {self.medecin} '
            f'le {self.date_rdv} à {self.heure_debut:%H:%M}'
        )

    def clean(self):
        """
        Validation métier : interdire les chevauchements dans l'agenda du médecin.

        Django appelle clean() AVANT de sauvegarder via un formulaire.
        On vérifie si, pour le même médecin et la même date, il existe déjà
        un RDV actif dont le créneau se chevauche avec le nôtre.

        Logique de chevauchement :
          RDV existant [A, B] chevauche [debut, fin] si A < fin ET B > debut
          (intersection de deux intervalles)
        """
        statuts_actifs = [self.StatutRdv.EN_ATTENTE, self.StatutRdv.CONFIRME]

        # On ne vérifie que pour les RDV actifs (pas les annulés ou terminés)
        if self.statut_rdv in statuts_actifs and self.medecin_id and self.date_rdv:
            chevauchements = RendezVous.objects.filter(
                medecin=self.medecin,
                date_rdv=self.date_rdv,
                statut_rdv__in=statuts_actifs,
                heure_debut__lt=self.heure_fin,    # l'existant commence avant la fin du nouveau
                heure_fin__gt=self.heure_debut,    # l'existant finit après le début du nouveau
            )
            # Exclure le RDV lui-même lors d'une modification (sinon conflit avec soi-même)
            if self.pk:
                chevauchements = chevauchements.exclude(pk=self.pk)
            if chevauchements.exists():
                raise ValidationError(
                    "Ce médecin a déjà un rendez-vous sur ce créneau."
                )

    # ------------------------------------------------------------------
    # Propriétés utilitaires — utilisées dans les templates et les vues
    # ------------------------------------------------------------------

    @property
    def est_annulable(self):
        """Un RDV est annulable seulement s'il est encore actif (pas terminé)."""
        return self.statut_rdv in [self.StatutRdv.EN_ATTENTE, self.StatutRdv.CONFIRME]

    @property
    def est_actif(self):
        """
        Vrai si le RDV est en cours de vie normale (pas annulé, pas terminé).
        Utilisé pour décider si le bouton de paiement doit être affiché.
        """
        return self.statut_rdv in [self.StatutRdv.EN_ATTENTE, self.StatutRdv.CONFIRME]
