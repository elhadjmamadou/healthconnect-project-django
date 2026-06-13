# ==============================================================================
# notifications/signals.py — Notifications automatiques par signaux Django
# ==============================================================================
# Les signaux Django permettent à des apps de "communiquer" sans couplage direct.
# On s'abonne à des événements (post_save, pre_save) et Django appelle nos
# fonctions automatiquement quand ces événements se produisent.
#
# Ce fichier gère 3 types de notifications :
#   1. Création d'un RDV → notification au médecin
#   2. Confirmation d'un RDV → notification au patient
#   3. Annulation d'un RDV → notification à l'autre partie
#   4. Confirmation d'un paiement → notification au patient
#
# IMPORTANT : Ce fichier doit être importé dans notifications/apps.py
# (méthode ready()) pour que les @receiver soient enregistrés au démarrage.
# ==============================================================================

import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from paiements.models import Paiement
from rendez_vous.models import RendezVous

from .email_sender import envoyer_email_notification
from .models import Notification

# Logger nommé pour ce module — visible dans les logs Django avec le préfixe 'notifications.signals'
logger = logging.getLogger(__name__)


# ==============================================================================
# FONCTIONS UTILITAIRES (privées — préfixe _ par convention)
# ==============================================================================

def _creer_notification(utilisateur, type_notification, contenu_resume, rendez_vous=None):
    """
    Crée une notification en base de données et tente d'envoyer un email.

    Args:
        utilisateur: L'objet User destinataire de la notification.
        type_notification: Une valeur de Notification.TypeNotification.
        contenu_resume (str): Texte affiché dans l'interface et l'email.
        rendez_vous: L'objet RendezVous associé (optionnel).

    Returns:
        L'objet Notification créé, ou None si l'utilisateur est inactif.
    """
    # Vérification de sécurité : pas de notification à un compte désactivé
    if not utilisateur or not utilisateur.is_active:
        return None

    notification = Notification.objects.create(
        utilisateur=utilisateur,
        rendez_vous=rendez_vous,
        type_notification=type_notification,
        contenu_resume=contenu_resume,
        statut_notification=Notification.StatutNotification.ENVOYE,
    )

    # Tentative d'envoi email — on log l'erreur sans faire échouer la sauvegarde
    # car une notification en base vaut mieux qu'une exception non gérée
    try:
        envoyer_email_notification(notification)
    except Exception as exc:
        logger.warning(
            'Échec de l\'envoi d\'email pour la notification %s : %s',
            notification.pk, exc
        )

    return notification


# ------------------------------------------------------------------
# Fonctions de génération du texte des notifications
# Centralisées ici pour être facilement modifiables sans toucher à la logique
# ------------------------------------------------------------------

def _texte_rdv_creation(rdv):
    """Texte envoyé AU MÉDECIN quand un patient crée un RDV."""
    return (
        f'Nouvelle demande de rendez-vous le {rdv.date_rdv:%d/%m/%Y} '
        f'à {rdv.heure_debut:%H:%M} avec {rdv.patient}.'
    )


def _texte_rdv_confirmation_patient(rdv):
    """Texte envoyé AU PATIENT quand le médecin confirme son RDV."""
    return (
        f'Votre rendez-vous du {rdv.date_rdv:%d/%m/%Y} à '
        f'{rdv.heure_debut:%H:%M} a été confirmé par le médecin.'
    )


def _texte_rdv_annulation(rdv, annule_par):
    """
    Texte d'annulation — adapté selon qui annule.

    Si le patient annule → on notifie le médecin (et on dit "le patient")
    Si le médecin annule → on notifie le patient (et on dit "le médecin")
    """
    autre_partie = 'le médecin' if annule_par == 'patient' else 'le patient'
    return (
        f'Le rendez-vous du {rdv.date_rdv:%d/%m/%Y} à '
        f'{rdv.heure_debut:%H:%M} a été annulé par {autre_partie}.'
    )


def _texte_paiement_confirme(paiement):
    """Texte envoyé AU PATIENT quand son paiement est confirmé."""
    return (
        f'Votre paiement de {paiement.montant} {paiement.devise} '
        f'pour le rendez-vous du {paiement.rendez_vous.date_rdv:%d/%m/%Y} '
        f'a été confirmé.'
    )


# ==============================================================================
# SIGNAUX POUR LES RENDEZ-VOUS
# ==============================================================================

@receiver(pre_save, sender=RendezVous)
def _memoriser_statut_rdv(sender, instance, **kwargs):
    """
    Mémorise le statut AVANT la sauvegarde pour détecter les changements.

    Problème : dans post_save, l'objet est déjà sauvegardé avec le NOUVEAU statut.
    On ne sait plus quel était l'ancien statut pour savoir SI ça a changé.

    Solution : pre_save est appelé juste AVANT la sauvegarde.
    On lit l'ancien statut depuis la base et on le stocke comme attribut
    temporaire sur l'instance (instance._ancien_statut_rdv).
    post_save pourra le lire depuis cet attribut.

    instance.pk est None pour une création (nouvelle instance jamais sauvegardée).
    """
    if instance.pk:
        # Modification d'un RDV existant : on lit l'ancienne valeur en base
        try:
            ancien = sender.objects.get(pk=instance.pk)
            instance._ancien_statut_rdv = ancien.statut_rdv
        except sender.DoesNotExist:
            instance._ancien_statut_rdv = None
    else:
        # Création : pas d'ancien statut
        instance._ancien_statut_rdv = None


@receiver(post_save, sender=RendezVous)
def creer_notification_rdv(sender, instance, created, **kwargs):
    """
    Crée une notification à chaque événement significatif sur un RDV.

    created=True → le RDV vient d'être créé (premier save)
    created=False → le RDV vient d'être modifié

    Logique :
      1. Création → notifier le médecin (nouvelle demande)
      2. Modification vers CONFIRME → notifier le patient (RDV accepté)
      3. Modification vers ANNULE_* → notifier l'autre partie (qui n'a pas annulé)
    """
    if not instance.medecin or not instance.medecin.user:
        return  # Donnée incomplète, on ne peut pas notifier

    if created:
        # Un nouveau RDV vient d'être créé → le médecin doit être informé
        _creer_notification(
            utilisateur=instance.medecin.user,
            type_notification=Notification.TypeNotification.CONFIRMATION_RDV,
            contenu_resume=_texte_rdv_creation(instance),
            rendez_vous=instance,
        )
        return

    # Pour une modification : comparer ancien et nouveau statut
    ancien = getattr(instance, '_ancien_statut_rdv', None)  # mémorisé par pre_save
    nouveau = instance.statut_rdv

    # Cas 2 : statut passé à CONFIRME → notifier le patient
    if ancien != nouveau and nouveau == RendezVous.StatutRdv.CONFIRME:
        _creer_notification(
            utilisateur=instance.patient.user,
            type_notification=Notification.TypeNotification.CONFIRMATION_RDV,
            contenu_resume=_texte_rdv_confirmation_patient(instance),
            rendez_vous=instance,
        )
        return

    # Cas 3 : statut passé à ANNULE_PATIENT ou ANNULE_MEDECIN
    if ancien != nouveau and nouveau in [
        RendezVous.StatutRdv.ANNULE_PATIENT,
        RendezVous.StatutRdv.ANNULE_MEDECIN,
    ]:
        # Déterminer qui annule et qui doit être notifié
        if nouveau == RendezVous.StatutRdv.ANNULE_PATIENT:
            destinataire = instance.medecin.user    # le médecin est notifié
            annule_par   = 'patient'
        else:
            destinataire = instance.patient.user    # le patient est notifié
            annule_par   = 'medecin'

        _creer_notification(
            utilisateur=destinataire,
            type_notification=Notification.TypeNotification.ANNULATION_RDV,
            contenu_resume=_texte_rdv_annulation(instance, annule_par),
            rendez_vous=instance,
        )


# ==============================================================================
# SIGNAUX POUR LES PAIEMENTS
# ==============================================================================

@receiver(pre_save, sender=Paiement)
def _memoriser_statut_paiement(sender, instance, **kwargs):
    """
    Même mécanique que _memoriser_statut_rdv, mais pour les paiements.

    Mémorise le statut de paiement AVANT la sauvegarde pour détecter
    la transition vers CONFIRME dans post_save.
    """
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
    """
    Notifie le patient quand son paiement passe à l'état CONFIRME.

    On vérifie `ancien != CONFIRME` pour ne notifier QU'UNE FOIS,
    même si le paiement est sauvegardé plusieurs fois avec le statut CONFIRME.
    (Évite les doubles notifications en cas de webhook reçu deux fois.)

    En mode démo : PayerRDVView crée le Paiement directement avec statut CONFIRME
    → ancien = None, nouveau = CONFIRME → la condition est vraie → notification envoyée.
    """
    # Vérifier que la chaîne complète de relations existe avant d'accéder au patient
    if not instance.rendez_vous or not instance.rendez_vous.patient or not instance.rendez_vous.patient.user:
        return

    ancien  = getattr(instance, '_ancien_statut_paiement', None)
    nouveau = instance.statut_paiement

    # Notifier uniquement lors de la PREMIÈRE confirmation (pas à chaque save)
    if nouveau == Paiement.StatutPaiement.CONFIRME and ancien != Paiement.StatutPaiement.CONFIRME:
        _creer_notification(
            utilisateur=instance.rendez_vous.patient.user,
            type_notification=Notification.TypeNotification.PAIEMENT_CONFIRME,
            contenu_resume=_texte_paiement_confirme(instance),
            rendez_vous=instance.rendez_vous,
        )
