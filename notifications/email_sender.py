# ==============================================================================
# notifications/email_sender.py — Envoi d'emails de notification
# ==============================================================================
# Ce module expose une seule fonction : envoyer_email_notification().
# Elle est appelée depuis notifications/signals.py après chaque création
# de Notification en base de données.
#
# Fonctionnement :
#   1. On rend le template HTML de l'email (notifications/email/notification.html)
#   2. strip_tags() produit la version texte brut (pour les clients sans HTML)
#   3. send_mail() envoie l'email via le backend configuré dans settings.py
#
# En développement (EMAIL_BACKEND = console) → l'email s'affiche dans le terminal.
# En production (EMAIL_BACKEND = SMTP) → l'email est envoyé réellement.
# ==============================================================================

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def envoyer_email_notification(notification):
    """
    Envoie un email de notification à l'utilisateur destinataire.

    Args:
        notification: L'objet Notification avec utilisateur, type et contenu.

    La fonction est silencieuse si l'utilisateur n'a pas d'email (guard clause).
    fail_silently=False : en cas d'erreur SMTP, l'exception est levée et
    capturée dans signals.py qui la logue sans faire échouer la transaction.

    Deux versions de l'email sont envoyées simultanément :
      - html_message  : version enrichie (HTML avec mise en forme)
      - plain_message : version texte brut (strip_tags retire les balises HTML)
    Les clients email modernes affichent la version HTML, les vieux clients
    affichent la version texte.
    """
    # Guard clause : pas d'email si le destinataire n'a pas d'adresse
    if not notification.utilisateur or not notification.utilisateur.email:
        return

    # Objet de l'email : "HealthConnect — Confirmation de rendez-vous"
    subject = f'HealthConnect — {notification.get_type_notification_display()}'

    # Rendu du template HTML avec le contexte de la notification
    html_message = render_to_string(
        'notifications/email/notification.html',
        {'notification': notification}
    )

    # Version texte : strip_tags() supprime toutes les balises HTML
    plain_message = strip_tags(html_message)

    # Expéditeur depuis les settings (DEFAULT_FROM_EMAIL dans .env)
    from_email    = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@healthconnect.local')
    recipient_list = [notification.utilisateur.email]

    send_mail(
        subject=subject,
        message=plain_message,        # version texte brut (fallback)
        from_email=from_email,
        recipient_list=recipient_list,
        html_message=html_message,    # version HTML (prioritaire)
        fail_silently=False,          # lève une exception en cas d'erreur SMTP
    )
