import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from paiements.models import Paiement
from rendez_vous.models import RendezVous

from .email_sender import envoyer_email_notification
from .models import Notification

logger = logging.getLogger(__name__)


def _creer_notification(utilisateur, type_notification, contenu_resume, rendez_vous=None):
    if not utilisateur or not utilisateur.is_active:
        return None

    notification = Notification.objects.create(
        utilisateur=utilisateur,
        rendez_vous=rendez_vous,
        type_notification=type_notification,
        contenu_resume=contenu_resume,
        statut_notification=Notification.StatutNotification.ENVOYE,
    )

    try:
        envoyer_email_notification(notification)
    except Exception as exc:
        logger.warning('Échec de l’envoi d’email pour la notification %s : %s', notification.pk, exc)

    return notification


def _texte_rdv_creation(rdv):
    return (
        f'Nouvelle demande de rendez-vous le {rdv.date_rdv:%d/%m/%Y} '
        f'à {rdv.heure_debut:%H:%M} avec {rdv.patient}.'
    )


def _texte_rdv_confirmation_patient(rdv):
    return (
        f'Votre rendez-vous du {rdv.date_rdv:%d/%m/%Y} à '
        f'{rdv.heure_debut:%H:%M} a été confirmé par le médecin.'
    )


def _texte_rdv_annulation(rdv, annule_par):
    autre_partie = 'le médecin' if annule_par == 'patient' else 'le patient'
    return (
        f'Le rendez-vous du {rdv.date_rdv:%d/%m/%Y} à '
        f'{rdv.heure_debut:%H:%M} a été annulé par {autre_partie}.'
    )


def _texte_paiement_confirme(paiement):
    return (
        f'Votre paiement de {paiement.montant} {paiement.devise} '
        f'pour le rendez-vous du {paiement.rendez_vous.date_rdv:%d/%m/%Y} '
        f'a été confirmé.'
    )


@receiver(pre_save, sender=RendezVous)
def _memoriser_statut_rdv(sender, instance, **kwargs):
    if instance.pk:
        try:
            ancien = sender.objects.get(pk=instance.pk)
            instance._ancien_statut_rdv = ancien.statut_rdv
        except sender.DoesNotExist:
            instance._ancien_statut_rdv = None
    else:
        instance._ancien_statut_rdv = None


@receiver(post_save, sender=RendezVous)
def creer_notification_rdv(sender, instance, created, **kwargs):
    if not instance.medecin or not instance.medecin.user:
        return

    if created:
        _creer_notification(
            utilisateur=instance.medecin.user,
            type_notification=Notification.TypeNotification.CONFIRMATION_RDV,
            contenu_resume=_texte_rdv_creation(instance),
            rendez_vous=instance,
        )
        return

    ancien = getattr(instance, '_ancien_statut_rdv', None)
    nouveau = instance.statut_rdv

    if ancien != nouveau and nouveau == RendezVous.StatutRdv.CONFIRME:
        _creer_notification(
            utilisateur=instance.patient.user,
            type_notification=Notification.TypeNotification.CONFIRMATION_RDV,
            contenu_resume=_texte_rdv_confirmation_patient(instance),
            rendez_vous=instance,
        )
        return

    if ancien != nouveau and nouveau in [
        RendezVous.StatutRdv.ANNULE_PATIENT,
        RendezVous.StatutRdv.ANNULE_MEDECIN,
    ]:
        if nouveau == RendezVous.StatutRdv.ANNULE_PATIENT:
            destinataire = instance.medecin.user
            annule_par = 'patient'
        else:
            destinataire = instance.patient.user
            annule_par = 'medecin'

        _creer_notification(
            utilisateur=destinataire,
            type_notification=Notification.TypeNotification.ANNULATION_RDV,
            contenu_resume=_texte_rdv_annulation(instance, annule_par),
            rendez_vous=instance,
        )


@receiver(pre_save, sender=Paiement)
def _memoriser_statut_paiement(sender, instance, **kwargs):
    if instance.pk:
        try:
            ancien = sender.objects.get(pk=instance.pk)
            instance._ancien_statut_paiement = ancien.statut_paiement
        except sender.DoesNotExist:
            instance._ancien_statut_paiement = None
    else:
        instance._ancien_statut_paiement = None


@receiver(post_save, sender=Paiement)
def creer_notification_paiement(sender, instance, created, **kwargs):
    if not instance.rendez_vous or not instance.rendez_vous.patient or not instance.rendez_vous.patient.user:
        return

    ancien = getattr(instance, '_ancien_statut_paiement', None)
    nouveau = instance.statut_paiement

    if nouveau == Paiement.StatutPaiement.CONFIRME and ancien != Paiement.StatutPaiement.CONFIRME:
        _creer_notification(
            utilisateur=instance.rendez_vous.patient.user,
            type_notification=Notification.TypeNotification.PAIEMENT_CONFIRME,
            contenu_resume=_texte_paiement_confirme(instance),
            rendez_vous=instance.rendez_vous,
        )
