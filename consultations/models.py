# ==============================================================================
# consultations/models.py — Dossiers médicaux, consultations et ordonnances
# ==============================================================================
# Cette app gère le cœur médical de la plateforme :
#   DossierMedical  → dossier permanent du patient (ouvert à l'inscription)
#   Consultation    → compte-rendu d'une visite médicale
#   Ordonnance      → ordonnance numérique signée électroniquement (QR code)
#   LigneOrdonnance → chaque médicament prescrit dans une ordonnance
# ==============================================================================

import uuid

from django.db import models


class DossierMedical(models.Model):
    """
    Dossier médical unique par patient.

    Il est créé automatiquement à la création du profil Patient
    (via un signal dans patients/signals.py). Il regroupe toutes
    les consultations du patient sur la plateforme.
    """

    class StatutDossier(models.TextChoices):
        ACTIF    = 'actif',    'Actif'       # dossier utilisable normalement
        ARCHIVE  = 'archive',  'Archivé'     # patient inactif, données conservées
        SUSPENDU = 'suspendu', 'Suspendu'    # dossier bloqué temporairement

    # OneToOneField : chaque patient n'a qu'UN seul dossier médical
    # related_name='dossier_medical' permet d'écrire patient.dossier_medical
    patient = models.OneToOneField(
        'patients.Patient',
        on_delete=models.CASCADE,
        related_name='dossier_medical',
        verbose_name='Patient',
    )

    # Numéro unique de dossier, généré automatiquement dans save() ci-dessous
    # Format : HC-XXXXXXXX (8 caractères hexadécimaux aléatoires)
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
    date_creation    = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    date_modification = models.DateTimeField(auto_now=True, verbose_name='Dernière modification')

    class Meta:
        verbose_name = 'Dossier médical'
        verbose_name_plural = 'Dossiers médicaux'
        ordering = ['-date_ouverture']

    def __str__(self):
        return f'Dossier {self.numero_dossier} — {self.patient}'

    def save(self, *args, **kwargs):
        """
        Génère le numéro de dossier à la première sauvegarde.

        uuid.uuid4().hex[:8] produit une chaîne hexadécimale de 8 caractères
        aléatoires. Le préfixe 'HC-' identifie le format HealthConnect.
        """
        if not self.numero_dossier:
            self.numero_dossier = 'HC-' + uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)

    @property
    def nombre_consultations(self):
        """Compte le nombre de consultations liées à ce dossier."""
        return self.consultations.count()


class Consultation(models.Model):
    """
    Compte-rendu d'une consultation médicale.

    Liée à un DossierMedical (historique patient), à un Médecin et
    optionnellement à un RendezVous (si la consultation découle d'un RDV pris
    en ligne). Le médecin renseigne le diagnostic, la prescription, etc.
    """

    # Lien vers le dossier du patient — un dossier peut avoir plusieurs consultations
    dossier = models.ForeignKey(
        DossierMedical,
        on_delete=models.CASCADE,
        related_name='consultations',
        verbose_name='Dossier médical',
    )

    # SET_NULL : si le médecin est supprimé, la consultation reste (archives)
    medecin = models.ForeignKey(
        'medecins.Medecin',
        on_delete=models.SET_NULL,
        null=True,
        related_name='consultations',
        verbose_name='Médecin',
    )

    # OneToOneField : un RDV donne lieu à AU PLUS une consultation
    rendez_vous = models.OneToOneField(
        'rendez_vous.RendezVous',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,           # blank=True : champ optionnel dans les formulaires
        related_name='consultation',
        verbose_name='Rendez-vous',
    )

    date_consultation = models.DateTimeField(verbose_name='Date et heure de la consultation')
    compte_rendu  = models.TextField(blank=True, verbose_name='Compte rendu')
    diagnostic    = models.TextField(blank=True, verbose_name='Diagnostic')
    prescription  = models.TextField(blank=True, verbose_name='Prescription')
    observations  = models.TextField(blank=True, verbose_name='Observations')
    date_creation    = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    date_modification = models.DateTimeField(auto_now=True, verbose_name='Dernière modification')

    class Meta:
        verbose_name = 'Consultation'
        verbose_name_plural = 'Consultations'
        ordering = ['-date_consultation']

    def __str__(self):
        return f'Consultation {self.dossier.patient} — {self.date_consultation:%d/%m/%Y %H:%M}'


class Ordonnance(models.Model):
    """
    Ordonnance numérique émise en fin de consultation.

    Chaque ordonnance possède :
      - un numéro unique lisible (ORD-XXXXXXXX)
      - un token UUID secret encodé dans le QR code, permettant à un
        pharmacien ou tiers de vérifier l'authenticité sur l'URL publique
        /consultations/ordonnance/verifier/<uuid>/
      - une liste de médicaments (LigneOrdonnance, relation inverse)
    """

    # OneToOneField : une consultation ne peut avoir qu'UNE ordonnance
    consultation = models.OneToOneField(
        Consultation,
        on_delete=models.CASCADE,
        related_name='ordonnance',
        verbose_name='Consultation',
    )

    # Numéro lisible, généré automatiquement dans save()
    numero = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Numéro d\'ordonnance',
    )

    # UUID aléatoire — ne JAMAIS l'exposer dans les URLs sauf pour la vérification
    # editable=False : champ non affiché dans l'admin (protège l'intégrité)
    token_verification = models.UUIDField(
        default=uuid.uuid4,     # généré automatiquement à la création
        unique=True,
        editable=False,
        verbose_name='Jeton de vérification',
        help_text='Encodé dans le QR code pour vérifier l\'authenticité',
    )

    # Recommandations globales : repos, régime alimentaire, suivi…
    instructions = models.TextField(
        blank=True,
        verbose_name='Instructions générales',
        help_text='Recommandations au patient (repos, régime, suivi…)',
    )

    # auto_now_add : rempli automatiquement à la création, non modifiable
    date_emission    = models.DateTimeField(auto_now_add=True, verbose_name='Date d\'émission')
    date_modification = models.DateTimeField(auto_now=True, verbose_name='Dernière modification')

    class Meta:
        verbose_name = 'Ordonnance'
        verbose_name_plural = 'Ordonnances'
        ordering = ['-date_emission']

    def __str__(self):
        return f'Ordonnance {self.numero} — {self.consultation.dossier.patient}'

    def save(self, *args, **kwargs):
        """Génère le numéro d'ordonnance (ORD-XXXXXXXX) à la première sauvegarde."""
        if not self.numero:
            self.numero = 'ORD-' + uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)

    # ------------------------------------------------------------------
    # Raccourcis pratiques — évitent d'écrire ordonnance.consultation.medecin
    # dans les templates et les vues
    # ------------------------------------------------------------------

    @property
    def medecin(self):
        """Médecin prescripteur (accès via la consultation liée)."""
        return self.consultation.medecin

    @property
    def patient(self):
        """Patient bénéficiaire de l'ordonnance (accès via le dossier médical)."""
        return self.consultation.dossier.patient


class LigneOrdonnance(models.Model):
    """
    Une ligne dans l'ordonnance = un médicament prescrit.

    Exemple :
      médicament = "Paracétamol 500 mg"
      posologie  = "1 comprimé matin, midi et soir"
      durée      = "5 jours"

    Le champ 'ordre' permet de trier les médicaments dans l'ordre
    où le médecin les a saisis (de haut en bas dans le formulaire).
    """

    # ForeignKey : une ordonnance a PLUSIEURS lignes
    ordonnance = models.ForeignKey(
        Ordonnance,
        on_delete=models.CASCADE,  # si l'ordonnance est supprimée, les lignes aussi
        related_name='lignes',
        verbose_name='Ordonnance',
    )

    medicament = models.CharField(max_length=150, verbose_name='Médicament')
    posologie  = models.CharField(
        max_length=150,
        verbose_name='Posologie',
        help_text='Ex : 1 comprimé matin et soir',
    )
    duree = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Durée',
        help_text='Ex : 7 jours',
    )
    # ordre = position de la ligne dans l'ordonnance (0, 1, 2…)
    ordre = models.PositiveSmallIntegerField(default=0, verbose_name='Ordre')

    class Meta:
        verbose_name = 'Ligne d\'ordonnance'
        verbose_name_plural = 'Lignes d\'ordonnance'
        ordering = ['ordre', 'id']  # tri par ordre de saisie puis par ID

    def __str__(self):
        return f'{self.medicament} — {self.posologie}'
