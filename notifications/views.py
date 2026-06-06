from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
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

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['nb_non_lues'] = Notification.objects.filter(
            utilisateur=self.request.user,
            statut_notification__in=[
                Notification.StatutNotification.EN_ATTENTE,
                Notification.StatutNotification.ENVOYE,
            ],
        ).count()
        return ctx


class MarquerLuView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notif = get_object_or_404(
            Notification,
            pk=pk,
            utilisateur=request.user,
        )
        if not notif.est_lu:
            notif.statut_notification = Notification.StatutNotification.LU
            notif.date_lecture = timezone.now()
            notif.save(update_fields=['statut_notification', 'date_lecture'])
        return JsonResponse({'status': 'ok', 'pk': pk})


class MarquerToutLuView(LoginRequiredMixin, View):
    def post(self, request):
        Notification.objects.filter(
            utilisateur=request.user,
            statut_notification__in=[
                Notification.StatutNotification.EN_ATTENTE,
                Notification.StatutNotification.ENVOYE,
            ],
        ).update(
            statut_notification=Notification.StatutNotification.LU,
            date_lecture=timezone.now(),
        )
        return redirect('notifications:liste')


class SupprimerNotificationView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notif = get_object_or_404(Notification, pk=pk, utilisateur=request.user)
        notif.delete()
        return redirect('notifications:liste')
