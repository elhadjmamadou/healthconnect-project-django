# ==============================================================================
# notifications/context_processors.py — Badge de notifications dans la navbar
# ==============================================================================
# Un context processor est une fonction appelée à CHAQUE requête Django.
# Elle injecte des variables dans le contexte de TOUS les templates,
# sans avoir à les passer manuellement depuis chaque vue.
#
# Ce processor injecte 'nb_notifs_non_lues' dans tous les templates →
# la navbar peut afficher le badge rouge avec le nombre de notifications
# non lues, partout dans l'application.
#
# Configuration : dans settings.py, TEMPLATES[0]['OPTIONS']['context_processors']
# contient 'notifications.context_processors.notifications_non_lues'.
# ==============================================================================

from .models import Notification


def notifications_non_lues(request):
    """
    Injecte le nombre de notifications non lues dans le contexte global.

    Appelée automatiquement par Django à chaque requête HTTP.

    Returns:
        dict: {'nb_notifs_non_lues': int}
              0 si l'utilisateur n'est pas connecté (évite l'AttributeError).

    Optimisation : une seule requête COUNT (pas de chargement des objets)
    car on n'a besoin que du nombre, pas du contenu des notifications.

    Les statuts "non lus" sont EN_ATTENTE et ENVOYE.
    Le statut LU signifie que l'utilisateur a cliqué sur la notification.
    """
    # Pas de requête BDD si l'utilisateur n'est pas authentifié
    if not request.user.is_authenticated:
        return {'nb_notifs_non_lues': 0}

    count = Notification.objects.filter(
        utilisateur=request.user,
        statut_notification__in=[
            Notification.StatutNotification.EN_ATTENTE,
            Notification.StatutNotification.ENVOYE,
        ],
    ).count()  # COUNT SQL : plus léger que len(queryset)

    return {'nb_notifs_non_lues': count}
