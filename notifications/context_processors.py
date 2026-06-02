from .models import Notification


def nb_notifs_non_lues(request):
    if not request.user.is_authenticated:
        return {}

    return {
        'nb_notifs_non_lues': Notification.objects.filter(
            utilisateur=request.user
        ).exclude(
            statut_notification=Notification.StatutNotification.LU
        ).count()
    }
