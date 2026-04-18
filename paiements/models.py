import uuid

from django.db import models


class Paiement(models.Model):

    class ModePaiement(models.TextChoices):
        ORANGE_MONEY = 'orange_money', 'Orange Money'
        MTN_MONEY = 'mtn_money', 'MTN Money'
        WAVE = 'wave', 'Wave'
        CARTE_BANCAIRE = 'carte_bancaire', 'Carte bancaire'
        ESPECES = 'especes', 'Espèces'

    class StatutPaiement(models.TextChoices):
        EN_ATTENTE = 'en_attente', 'En attente'
        INITIE = 'initie', 'Initié'
        CONFIRME = 'confirme', 'Confirmé'
        ECHOUE = 'echoue', 'Échoué'
        REMBOURSE = 'rembourse', 'Remboursé'

    rendez_vous = models.OneToOneField(
        'rendez_vous.RendezVous',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paiement',
        verbose_name='Rendez-vous',
    )
    consultation = models.ForeignKey(
        'consultations.Consultation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paiements',
        verbose_name='Consultation',
    )
    reference_interne = models.CharField(
        max_length=30,
        unique=True,
        verbose_name='Référence interne',
    )
    reference_djomy = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Référence Djomy',
        help_text='ID de transaction retourné par Djomy',
    )
    date_paiement = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Date de paiement',
    )
    montant = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Montant',
    )
    devise = models.CharField(max_length=5, default='GNF', verbose_name='Devise')
    mode_paiement = models.CharField(
        max_length=20,
        choices=ModePaiement.choices,
        default=ModePaiement.ORANGE_MONEY,
        verbose_name='Mode de paiement',
    )
    statut_paiement = models.CharField(
        max_length=15,
        choices=StatutPaiement.choices,
        default=StatutPaiement.EN_ATTENTE,
        verbose_name='Statut',
    )
    webhook_payload = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Payload webhook',
        help_text='Payload brut reçu du webhook Djomy',
    )
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    date_modification = models.DateTimeField(auto_now=True, verbose_name='Dernière modification')

    class Meta:
        verbose_name = 'Paiement'
        verbose_name_plural = 'Paiements'
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['statut_paiement']),
            models.Index(fields=['reference_djomy']),
        ]

    def __str__(self):
        return f'Paiement {self.reference_interne} — {self.montant} {self.devise}'

    def save(self, *args, **kwargs):
        if not self.reference_interne:
            self.reference_interne = 'PAY-' + uuid.uuid4().hex[:10].upper()
        super().save(*args, **kwargs)

    @property
    def est_paye(self):
        return self.statut_paiement == self.StatutPaiement.CONFIRME

    @property
    def est_en_attente(self):
        return self.statut_paiement in [
            self.StatutPaiement.EN_ATTENTE,
            self.StatutPaiement.INITIE,
        ]


class ConfigurationDjomy(models.Model):
    cle_api = models.CharField(
        max_length=255,
        verbose_name='Clé API',
        help_text='Lue depuis .env — ne pas stocker en clair en production',
    )
    url_base = models.CharField(
        max_length=255,
        default='https://api.djomy.africa/v1',
        verbose_name='URL de base',
    )
    url_webhook = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='URL webhook',
        help_text='URL de retour pour les webhooks Djomy',
    )
    actif = models.BooleanField(default=True, verbose_name='Actif')
    date_modification = models.DateTimeField(auto_now=True, verbose_name='Dernière modification')

    class Meta:
        verbose_name = 'Configuration Djomy'
        verbose_name_plural = 'Configurations Djomy'

    def __str__(self):
        return f'Configuration Djomy ({"actif" if self.actif else "inactif"})'
