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


class MarquerLuView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notification = get_object_or_404(
            Notification,
            pk=pk,
            utilisateur=request.user,
        )
        notification.statut_notification = Notification.StatutNotification.LU
        notification.date_lecture = timezone.now()
        notification.save(update_fields=['statut_notification', 'date_lecture'])
        return JsonResponse({'status': 'ok'})


class MarquerToutLuView(LoginRequiredMixin, View):
    def post(self, request):
        Notification.objects.filter(
            utilisateur=request.user
        ).exclude(
            statut_notification=Notification.StatutNotification.LU
        ).update(
            statut_notification=Notification.StatutNotification.LU,
            date_lecture=timezone.now(),
        )
        return redirect('notifications:liste')
