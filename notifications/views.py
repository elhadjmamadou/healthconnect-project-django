from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from .models import Notification


class ListeNotificationsView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = 'notifications/liste_notifications.html'
    context_object_name = 'notifications'
    paginate_by = 20

    def get_queryset(self):
        return Notification.objects.filter(
            utilisateur=self.request.user
        ).order_by('-date_envoi')
