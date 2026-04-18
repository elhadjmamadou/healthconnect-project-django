from django.db import models


class Specialite(models.Model):
    libelle = models.CharField(max_length=100, unique=True, verbose_name='Libellé')
    description = models.TextField(blank=True, verbose_name='Description')
    icone = models.CharField(max_length=50, blank=True, verbose_name='Icône Bootstrap', help_text="Ex : bi-heart-pulse")
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    date_modification = models.DateTimeField(auto_now=True, verbose_name='Dernière modification')

    class Meta:
        verbose_name = 'Spécialité'
        verbose_name_plural = 'Spécialités'
        ordering = ['libelle']

    def __str__(self):
        return self.libelle


class Medecin(models.Model):

    class ModeExercice(models.TextChoices):
        LIBERAL = 'liberal', 'Libéral'
        SALARIE = 'salarie', 'Salarié'
        MIXTE = 'mixte', 'Mixte'

    user = models.OneToOneField(
        'users.User',
        on_delete=models.CASCADE,
        related_name='medecin_profile',
        verbose_name='Utilisateur',
    )
    numero_ordre = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Numéro d'ordre",
    )
    biographie = models.TextField(blank=True, verbose_name='Biographie')
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
    specialites = models.ManyToManyField(
        Specialite,
        blank=True,
        related_name='medecins',
        verbose_name='Spécialités',
    )
    accepte_nouveaux_patients = models.BooleanField(
        default=True,
        verbose_name='Accepte de nouveaux patients',
    )
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    date_modification = models.DateTimeField(auto_now=True, verbose_name='Dernière modification')

    class Meta:
        verbose_name = 'Médecin'
        verbose_name_plural = 'Médecins'
        ordering = ['user__last_name', 'user__first_name']

    def __str__(self):
        return f'Dr. {self.nom_complet}'

    @property
    def nom_complet(self):
        return self.user.get_full_name() or self.user.email

    @property
    def specialites_list(self):
        return list(self.specialites.values_list('libelle', flat=True))
