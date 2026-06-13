# ==============================================================================
# medecins/models.py — Profils médecins et spécialités médicales
# ==============================================================================
# Cette app gère les deux entités liées aux praticiens :
#   Specialite : domaine médical (cardiologie, pédiatrie…)
#   Medecin    : profil professionnel lié à un User (relation OneToOne)
#
# Un médecin peut avoir PLUSIEURS spécialités (ManyToManyField).
# Un médecin ne peut avoir qu'UN seul compte User (OneToOneField).
# ==============================================================================

from django.db import models


class Specialite(models.Model):
    """
    Spécialité médicale (ex : Cardiologie, Pédiatrie, Dermatologie…).

    Utilisée dans l'annuaire pour filtrer les médecins et dans les profils
    pour indiquer le domaine d'expertise. L'icône correspond à un nom de
    symbole Material Symbols Outlined (police d'icônes Google utilisée dans l'UI).
    """

    # unique=True : deux spécialités ne peuvent pas avoir le même libellé
    libelle     = models.CharField(max_length=100, unique=True, verbose_name='Libellé')
    description = models.TextField(blank=True, verbose_name='Description')

    # Nom de l'icône Material Symbols (ex : "stethoscope", "cardiology", "healing")
    # Affiché dans les templates avec <span class="material-symbols-outlined">{{ spec.icone }}</span>
    icone = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Icône Bootstrap',
        help_text='Ex : bi-heart-pulse'
    )

    date_creation    = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    date_modification = models.DateTimeField(auto_now=True, verbose_name='Dernière modification')

    class Meta:
        verbose_name = 'Spécialité'
        verbose_name_plural = 'Spécialités'
        ordering = ['libelle']   # tri alphabétique dans tous les sélecteurs

    def __str__(self):
        return self.libelle


class Medecin(models.Model):
    """
    Profil professionnel d'un médecin inscrit sur HealthConnect.

    La relation avec User est OneToOneField (1 médecin = 1 compte).
    Les données d'identité (prénom, nom, email) sont sur User.
    Les données professionnelles (numéro d'ordre, tarif…) sont ici.

    related_name='medecin_profile' permet d'écrire :
      user.medecin_profile.tarif_consultation
    depuis n'importe quel objet User dans les vues et templates.
    """

    # Mode d'exercice de la médecine
    class ModeExercice(models.TextChoices):
        LIBERAL = 'liberal', 'Libéral'  # cabinet privé
        SALARIE = 'salarie', 'Salarié'  # structure publique ou clinique
        MIXTE   = 'mixte',   'Mixte'    # les deux à la fois

    # Lien vers le compte utilisateur (données d'identité + authentification)
    # CASCADE : supprimer le User supprime aussi le profil médecin
    user = models.OneToOneField(
        'users.User',
        on_delete=models.CASCADE,
        related_name='medecin_profile',
        verbose_name='Utilisateur',
    )

    # Numéro d'ordre du Conseil national de l'Ordre des médecins de Guinée
    # unique=True : deux médecins ne peuvent pas avoir le même numéro
    numero_ordre = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Numéro d'ordre",
    )

    biographie = models.TextField(blank=True, verbose_name='Biographie')

    # Tarif en Francs guinéens (GNF) — 0 = "Sur demande" affiché dans l'annuaire
    tarif_consultation = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Tarif consultation',
    )

    mode_exercice = models.CharField(
        max_length=10,
        choices=ModeExercice.choices,
        default=ModeExercice.LIBERAL,
        verbose_name="Mode d'exercice",
    )

    # ManyToManyField : un médecin peut avoir plusieurs spécialités
    # blank=True : un médecin peut ne pas avoir de spécialité renseignée
    # related_name='medecins' permet d'écrire specialite.medecins.all()
    specialites = models.ManyToManyField(
        Specialite,
        blank=True,
        related_name='medecins',
        verbose_name='Spécialités',
    )

    # Si False → le médecin n'apparaît plus dans l'annuaire avec le bouton "Prendre RDV"
    accepte_nouveaux_patients = models.BooleanField(
        default=True,
        verbose_name='Accepte de nouveaux patients',
    )

    date_creation    = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    date_modification = models.DateTimeField(auto_now=True, verbose_name='Dernière modification')

    class Meta:
        verbose_name = 'Médecin'
        verbose_name_plural = 'Médecins'
        ordering = ['user__last_name', 'user__first_name']   # tri alphabétique

    def __str__(self):
        return f'Dr. {self.nom_complet}'

    # ------------------------------------------------------------------
    # Propriétés — évitent de répéter medecin.user.get_full_name() partout
    # ------------------------------------------------------------------

    @property
    def nom_complet(self):
        """
        Retourne le nom complet du médecin.
        Fallback sur l'email si prénom/nom ne sont pas renseignés.
        """
        return self.user.get_full_name() or self.user.email

    @property
    def specialites_list(self):
        """Retourne la liste des libellés de spécialités (pour sérialisation JSON)."""
        return list(self.specialites.values_list('libelle', flat=True))
