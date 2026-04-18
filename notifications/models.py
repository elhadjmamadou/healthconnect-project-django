from django.db import models
from django.utils import timezone


class Notification(models.Model):

    class TypeNotification(models.TextChoices):
        CONFIRMATION_RDV = 'confirmation_rdv', 'Confirmation de rendez-vous'
        RAPPEL_RDV = 'rappel_rdv', 'Rappel de rendez-vous'
        ANNULATION_RDV = 'annulation_rdv', 'Annulation de rendez-vous'
        MODIFICATION_RDV = 'modification_rdv', 'Modification de rendez-vous'
        PAIEMENT_CONFIRME = 'paiement_confirme', 'Paiement confirmé'
        PAIEMENT_ECHOUE = 'paiement_echoue', 'Paiement échoué'
        INFO_GENERALE = 'info_generale', 'Information générale'

    class Canal(models.TextChoices):
        APPLICATION = 'application', 'Application'
        EMAIL = 'email', 'Email'
        SMS = 'sms', 'SMS'

    class StatutNotification(models.TextChoices):
        EN_ATTENTE = 'en_attente', 'En attente'
        ENVOYE = 'envoye', 'Envoyé'
        LU = 'lu', 'Lu'
        ECHOUE = 'echoue', 'Échoué'

    utilisateur = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='Utilisateur',
    )
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
    contenu_resume = models.TextField(verbose_name='Contenu')
    date_envoi = models.DateTimeField(auto_now_add=True, verbose_name="Date d'envoi")
    statut_notification = models.CharField(
        max_length=15,
        choices=StatutNotification.choices,
        default=StatutNotification.EN_ATTENTE,
        verbose_name='Statut',
    )
    date_lecture = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Date de lecture',
    )

    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-date_envoi']
        indexes = [
            models.Index(fields=['utilisateur', 'statut_notification']),
            models.Index(fields=['date_envoi']),
        ]

    def __str__(self):
        return f'{self.get_type_notification_display()} — {self.utilisateur}'

    @property
    def est_lu(self):
        return self.statut_notification == self.StatutNotification.LU

    @property
    def est_recent(self):
        from datetime import timedelta
        return (timezone.now() - self.date_envoi) < timedelta(hours=24)
