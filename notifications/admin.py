from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('utilisateur', 'type_notification', 'canal', 'statut_notification', 'date_envoi')
    list_filter = ('type_notification', 'canal', 'statut_notification')
    search_fields = ('utilisateur__email', 'utilisateur__first_name', 'contenu_resume')
    date_hierarchy = 'date_envoi'
    raw_id_fields = ('utilisateur', 'rendez_vous')
