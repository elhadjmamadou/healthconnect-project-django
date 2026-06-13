# ==============================================================================
# paiements/models.py — Modèles de paiement mobile money (Djomy)
# ==============================================================================
# Djomy est un agrégateur de paiement mobile money guinéen qui regroupe
# Orange Money, MTN Money et Wave. Dans cet environnement de démonstration,
# les paiements sont simulés côté serveur (pas d'appel API réel).
# ==============================================================================

import uuid

from django.db import models


class Paiement(models.Model):
    """
    Enregistrement d'un paiement de consultation.

    Chaque paiement est lié à un RendezVous (OneToOneField) et/ou à une
    Consultation (ForeignKey). Il possède deux références :
      - reference_interne : générée par HealthConnect (PAY-XXXXXXXXXX)
      - reference_djomy   : ID de transaction retourné par l'API Djomy
                            (en simulation : DJM-SIM-XXXXXXXXXX)
    """

    # ------------------------------------------------------------------
    # Modes de paiement disponibles
    # Les 3 premiers sont les opérateurs mobile money guinéens affichés
    # dans le formulaire de paiement. Les 2 derniers sont pour l'admin.
    # ------------------------------------------------------------------
    class ModePaiement(models.TextChoices):
        ORANGE_MONEY  = 'orange_money',  'Orange Money'
        MTN_MONEY     = 'mtn_money',     'MTN Money'
        WAVE          = 'wave',          'Wave'
        CARTE_BANCAIRE = 'carte_bancaire', 'Carte bancaire'
        ESPECES       = 'especes',       'Espèces'

    # ------------------------------------------------------------------
    # Cycle de vie du paiement
    # EN_ATTENTE → INITIE → CONFIRME (succès) ou ECHOUE
    #                     ↘ REMBOURSE (en cas de litige)
    # ------------------------------------------------------------------
    class StatutPaiement(models.TextChoices):
        EN_ATTENTE = 'en_attente', 'En attente'   # paiement créé, pas encore soumis
        INITIE     = 'initie',     'Initié'        # demande envoyée à Djomy
        CONFIRME   = 'confirme',   'Confirmé'      # transaction validée (ou simulée)
        ECHOUE     = 'echoue',     'Échoué'        # échec de la transaction
        REMBOURSE  = 'rembourse',  'Remboursé'     # remboursement effectué

    # OneToOneField : un RDV ne peut être payé qu'UNE fois
    rendez_vous = models.OneToOneField(
        'rendez_vous.RendezVous',
        on_delete=models.SET_NULL,   # SET_NULL : garde le paiement si le RDV est supprimé
        null=True,
        blank=True,
        related_name='paiement',
        verbose_name='Rendez-vous',
    )

    # Lien optionnel vers la consultation (pour les paiements post-consultation)
    consultation = models.ForeignKey(
        'consultations.Consultation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paiements',
        verbose_name='Consultation',
    )

    # Référence interne unique, générée dans save() → format PAY-XXXXXXXXXX
    reference_interne = models.CharField(
        max_length=30,
        unique=True,
        verbose_name='Référence interne',
    )

    # Référence retournée par l'API Djomy (vide jusqu'à confirmation)
    reference_djomy = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Référence Djomy',
        help_text='ID de transaction retourné par Djomy',
    )

    # null=True car la date n'est connue qu'à la confirmation du paiement
    date_paiement = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Date de paiement',
    )

    # max_digits=10 / decimal_places=2 : jusqu'à 9 999 999 999,99 GNF
    montant = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Montant',
    )

    # Devise : GNF (Franc guinéen) par défaut
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

    # JSONField stocke le payload brut du webhook Djomy (dict Python ↔ JSON en BDD)
    # En simulation, il contient {'simulation': True, 'status': 'success', ...}
    webhook_payload = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Payload webhook',
        help_text='Payload brut reçu du webhook Djomy',
    )

    date_creation    = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    date_modification = models.DateTimeField(auto_now=True, verbose_name='Dernière modification')

    class Meta:
        verbose_name = 'Paiement'
        verbose_name_plural = 'Paiements'
        ordering = ['-date_creation']
        indexes = [
            # Accélère les filtres par statut (requêtes fréquentes dans le dashboard)
            models.Index(fields=['statut_paiement']),
            # Accélère la recherche par référence Djomy (réception des webhooks)
            models.Index(fields=['reference_djomy']),
        ]

    def __str__(self):
        return f'Paiement {self.reference_interne} — {self.montant} {self.devise}'

    def save(self, *args, **kwargs):
        """Génère la référence interne (PAY-XXXXXXXXXX) à la première sauvegarde."""
        if not self.reference_interne:
            # hex[:10] → 10 caractères hexadécimaux pseudo-aléatoires
            self.reference_interne = 'PAY-' + uuid.uuid4().hex[:10].upper()
        super().save(*args, **kwargs)

    # ------------------------------------------------------------------
    # Propriétés utilisées dans les templates pour les conditions d'affichage
    # ------------------------------------------------------------------

    @property
    def est_paye(self):
        """Vrai si le paiement a été confirmé (statut = CONFIRME)."""
        return self.statut_paiement == self.StatutPaiement.CONFIRME

    @property
    def est_en_attente(self):
        """Vrai si le paiement est en cours de traitement (pas encore confirmé ni échoué)."""
        return self.statut_paiement in [
            self.StatutPaiement.EN_ATTENTE,
            self.StatutPaiement.INITIE,
        ]


class ConfigurationDjomy(models.Model):
    """
    Paramètres de connexion à l'API Djomy (stockage admin).

    En production, les valeurs sensibles (cle_api, webhook_secret) sont lues
    depuis le fichier .env via django-environ. Ce modèle permet à l'admin
    de vérifier la configuration sans accéder au serveur.
    """

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
