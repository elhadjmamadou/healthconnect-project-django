from .models import Notification


def notifications_non_lues(request):
    if not request.user.is_authenticated:
        return {'nb_notifs_non_lues': 0}

    count = Notification.objects.filter(
        utilisateur=request.user,
        statut_notification__in=[
            Notification.StatutNotification.EN_ATTENTE,
            Notification.StatutNotification.ENVOYE,
        ],
    ).count()
    return {'nb_notifs_non_lues': count}
