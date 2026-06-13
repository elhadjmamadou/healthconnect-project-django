# ==============================================================================
# notifications/views.py — Gestion des notifications utilisateur
# ==============================================================================
# Ce fichier contient 4 vues pour le centre de notifications :
#
# ListeNotificationsView  : affiche toutes les notifications paginées
# MarquerLuView           : marque UNE notification comme lue (AJAX-friendly)
# MarquerToutLuView       : marque TOUTES les notifications non lues en une requête
# SupprimerNotificationView : supprime une notification de la base de données
#
# Chaque vue filtre sur utilisateur=request.user pour garantir qu'un
# utilisateur ne peut jamais lire ou modifier les notifications d'un autre.
# ==============================================================================

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import ListView

from .models import Notification


class ListeNotificationsView(LoginRequiredMixin, ListView):
    """
    Affiche toutes les notifications de l'utilisateur connecté, paginées.

    paginate_by = 20 : Django découpe automatiquement le queryset en pages
    de 20 éléments et injecte 'page_obj' dans le contexte du template.

    get_context_data() ajoute 'nb_non_lues' pour afficher le badge rouge
    en haut de la page (différent du context_processor qui sert la navbar).

    Les statuts EN_ATTENTE et ENVOYE sont considérés "non lus" —
    le statut LU signifie que l'utilisateur a explicitement cliqué sur la notif.
    """

    model = Notification
    template_name = 'notifications/liste_notifications.html'
    context_object_name = 'notifications'
    paginate_by = 20  # pagination automatique Django, 20 notifs par page

    def get_queryset(self):
        """Retourne uniquement les notifications de l'utilisateur connecté, plus récentes en premier."""
        return Notification.objects.filter(
            utilisateur=self.request.user
        ).order_by('-date_envoi')  # ordre décroissant : la plus récente en tête

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Compteur SQL (COUNT) → plus léger que len(queryset) car ne charge pas les objets
        ctx['nb_non_lues'] = Notification.objects.filter(
            utilisateur=self.request.user,
            statut_notification__in=[
                Notification.StatutNotification.EN_ATTENTE,
                Notification.StatutNotification.ENVOYE,
            ],
        ).count()
        return ctx


class MarquerLuView(LoginRequiredMixin, View):
    """
    Marque UNE notification comme lue.

    Réponse JSON : compatible avec les appels AJAX depuis le template.
    Le template peut appeler cette URL en fetch() et mettre à jour le badge
    sans recharger la page.

    save(update_fields=['statut_notification', 'date_lecture']) :
    → UPDATE SQL qui ne touche QUE ces deux colonnes (pas un UPDATE * de toute la ligne).
    → Plus performant : évite les conflits si d'autres champs sont modifiés en parallèle.
    → Bonne pratique Django quand on sait exactement quels champs ont changé.

    Guard clause : if not notif.est_lu → idempotent, pas de double-écriture.
    """

    def post(self, request, pk):
        # Sécurité : get_object_or_404 lève un 404 si la notif n'appartient pas à l'utilisateur
        notif = get_object_or_404(
            Notification,
            pk=pk,
            utilisateur=request.user,  # impossible de marquer la notif d'un autre
        )
        if not notif.est_lu:
            notif.statut_notification = Notification.StatutNotification.LU
            notif.date_lecture = timezone.now()  # horodatage précis de la lecture
            # UPDATE SQL partiel : ne modifie que les 2 colonnes concernées
            notif.save(update_fields=['statut_notification', 'date_lecture'])
        # Réponse JSON pour les appels AJAX (pas de rechargement de page nécessaire)
        return JsonResponse({'status': 'ok', 'pk': pk})


class MarquerToutLuView(LoginRequiredMixin, View):
    """
    Marque TOUTES les notifications non lues de l'utilisateur comme lues.

    .update(...) : génère un seul UPDATE SQL avec WHERE sur toutes les lignes
    correspondantes. C'est un "bulk update" — beaucoup plus performant qu'une
    boucle Python qui appellerait notif.save() pour chaque notification.

    Exemple SQL généré :
      UPDATE notifications_notification
      SET statut_notification='lu', date_lecture=NOW()
      WHERE utilisateur_id=42
        AND statut_notification IN ('en_attente', 'envoye');

    Redirige vers la liste (pas de JSON ici car c'est une action de formulaire classique).
    """

    def post(self, request):
        # Un seul UPDATE SQL pour toutes les notifications non lues
        Notification.objects.filter(
            utilisateur=request.user,
            statut_notification__in=[
                Notification.StatutNotification.EN_ATTENTE,
                Notification.StatutNotification.ENVOYE,
            ],
        ).update(
            statut_notification=Notification.StatutNotification.LU,
            date_lecture=timezone.now(),  # même timestamp pour toutes les notifs marquées
        )
        return redirect('notifications:liste')


class SupprimerNotificationView(LoginRequiredMixin, View):
    """
    Supprime définitivement une notification.

    Le filtre utilisateur=request.user dans get_object_or_404 est la protection
    principale : un utilisateur ne peut pas supprimer la notification d'un autre
    même s'il connaît l'ID dans l'URL.

    patient.user.delete() n'est pas utilisé ici — c'est une suppression douce
    de la notification uniquement, pas du compte utilisateur.
    """

    def post(self, request, pk):
        # 404 si la notif n'existe pas ou n'appartient pas à l'utilisateur
        notif = get_object_or_404(Notification, pk=pk, utilisateur=request.user)
        notif.delete()  # DELETE SQL sur cette seule ligne
        return redirect('notifications:liste')
