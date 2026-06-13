# ==============================================================================
# notifications/models.py — Modèle de notification in-app et email
# ==============================================================================
# Une notification informe un utilisateur d'un événement important :
# confirmation de RDV, annulation, paiement confirmé…
#
# Chaque notification a un cycle de vie : EN_ATTENTE → ENVOYE → LU.
# Les notifications sont créées automatiquement par les signaux Django
# définis dans notifications/signals.py.
#
# Multi-canal prévu : APPLICATION (interface web), EMAIL, SMS.
# Actuellement, seuls APPLICATION et EMAIL sont implémentés.
# ==============================================================================

from django.db import models
from django.utils import timezone


class Notification(models.Model):
    """
    Notification envoyée à un utilisateur suite à un événement sur la plateforme.

    Créée automatiquement par notifications/signals.py dans les cas suivants :
      - Nouveau RDV créé → notification au médecin
      - RDV confirmé → notification au patient
      - RDV annulé → notification à l'autre partie
      - Paiement confirmé → notification au patient
    """

    # ------------------------------------------------------------------
    # Types de notification — détermine le message et l'icône affichés
    # ------------------------------------------------------------------
    class TypeNotification(models.TextChoices):
        CONFIRMATION_RDV  = 'confirmation_rdv',  'Confirmation de rendez-vous'
        RAPPEL_RDV        = 'rappel_rdv',        'Rappel de rendez-vous'
        ANNULATION_RDV    = 'annulation_rdv',    'Annulation de rendez-vous'
        MODIFICATION_RDV  = 'modification_rdv',  'Modification de rendez-vous'
        PAIEMENT_CONFIRME = 'paiement_confirme', 'Paiement confirmé'
        PAIEMENT_ECHOUE   = 'paiement_echoue',   'Paiement échoué'
        INFO_GENERALE     = 'info_generale',     'Information générale'

    # Canal de diffusion — extensible pour SMS via une passerelle future
    class Canal(models.TextChoices):
        APPLICATION = 'application', 'Application'
        EMAIL       = 'email',       'Email'
        SMS         = 'sms',         'SMS'

    # Cycle de vie de la notification
    class StatutNotification(models.TextChoices):
        EN_ATTENTE = 'en_attente', 'En attente'  # créée, pas encore envoyée
        ENVOYE     = 'envoye',     'Envoyé'      # email/notification envoyée
        LU         = 'lu',         'Lu'          # l'utilisateur l'a lue
        ECHOUE     = 'echoue',     'Échoué'      # échec de l'envoi email

    # ForeignKey : un utilisateur peut recevoir PLUSIEURS notifications
    # CASCADE : si l'utilisateur est supprimé, ses notifications aussi
    # related_name='notifications' → user.notifications.all()
    utilisateur = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='Utilisateur',
    )

    # RDV associé (optionnel — pas de RDV pour les notifications générales)
    # SET_NULL : si le RDV est supprimé, la notification reste sans lien RDV
    rendez_vous = models.ForeignKey(
        'rendez_vous.RendezVous',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name='Rendez-vous',
    )

    type_notification = models.CharField(
        max_length=25,
        choices=TypeNotification.choices,
        verbose_name='Type',
    )

    canal = models.CharField(
        max_length=15,
        choices=Canal.choices,
        default=Canal.APPLICATION,
        verbose_name='Canal',
    )

    # Texte principal de la notification (affiché dans l'interface et l'email)
    contenu_resume = models.TextField(verbose_name='Contenu')

    # Horodatage automatique à la création
    date_envoi = models.DateTimeField(auto_now_add=True, verbose_name="Date d'envoi")

    statut_notification = models.CharField(
        max_length=15,
        choices=StatutNotification.choices,
        default=StatutNotification.EN_ATTENTE,
        verbose_name='Statut',
    )

    # Rempli quand l'utilisateur clique sur la notification dans l'interface
    date_lecture = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Date de lecture',
    )

    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-date_envoi']  # les plus récentes en premier
        indexes = [
            # Index composé : accélère la requête "notifications non lues d'un utilisateur"
            # (utilisée pour le badge de notification dans la navbar)
            models.Index(fields=['utilisateur', 'statut_notification']),
            models.Index(fields=['date_envoi']),
        ]

    def __str__(self):
        # get_type_notification_display() retourne le libellé lisible du type
        return f'{self.get_type_notification_display()} — {self.utilisateur}'

    # ------------------------------------------------------------------
    # Propriétés utilitaires — utilisées dans les templates et la navbar
    # ------------------------------------------------------------------

    @property
    def est_lu(self):
        """Vrai si la notification a été lue par l'utilisateur."""
        return self.statut_notification == self.StatutNotification.LU

    @property
    def est_recent(self):
        """
        Vrai si la notification a moins de 24 heures.

        Utilisé pour afficher un badge "Nouveau" sur les notifications récentes.
        timezone.now() retourne un datetime avec timezone aware (fuseau horaire
        Africa/Conakry selon les settings).
        """
        from datetime import timedelta
        return (timezone.now() - self.date_envoi) < timedelta(hours=24)
