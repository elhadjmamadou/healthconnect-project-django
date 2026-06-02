from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def envoyer_email_notification(notification):
    if not notification.utilisateur or not notification.utilisateur.email:
        return

    subject = f'HealthConnect — {notification.get_type_notification_display()}'
    html_message = render_to_string(
        'notifications/email/notification.html',
        {'notification': notification}
    )
    plain_message = strip_tags(html_message)
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@healthconnect.local')
    recipient_list = [notification.utilisateur.email]

    send_mail(
        subject=subject,
        message=plain_message,
        from_email=from_email,
        recipient_list=recipient_list,
        html_message=html_message,
        fail_silently=False,
    )
