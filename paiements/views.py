import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.db.models import Sum
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView

from .models import Paiement


class ListePaiementsView(LoginRequiredMixin, ListView):
    model = Paiement
    template_name = 'paiements/liste_paiements.html'
    context_object_name = 'paiements'
    paginate_by = 20

    def get_queryset(self):
        qs = Paiement.objects.select_related(
            'rendez_vous__patient__user',
            'rendez_vous__medecin__user',
            'consultation__dossier__patient__user',
            'consultation__medecin__user',
        )
        user = self.request.user
        if user.is_patient:
            qs = qs.filter(
                models.Q(rendez_vous__patient__user=user)
                | models.Q(consultation__dossier__patient__user=user)
            )
        elif user.is_medecin:
            qs = qs.filter(
                models.Q(rendez_vous__medecin__user=user)
                | models.Q(consultation__medecin__user=user)
            )

        statut = self.request.GET.get('statut', '')
        mode = self.request.GET.get('mode', '')
        if statut:
            qs = qs.filter(statut_paiement=statut)
        if mode:
            qs = qs.filter(mode_paiement=mode)

        return qs.order_by('-date_creation')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.localdate()
        month_start = today.replace(day=1)
        qs_month = Paiement.objects.filter(date_creation__date__gte=month_start)

        ctx['kpi'] = {
            'total_encaisse': qs_month.filter(statut_paiement='confirme').aggregate(t=Sum('montant'))['t'] or 0,
            'en_attente': qs_month.filter(statut_paiement__in=['en_attente', 'initie']).count(),
            'echoues': qs_month.filter(statut_paiement='echoue').count(),
        }
        ctx['selected_statut'] = self.request.GET.get('statut', '')
        ctx['selected_mode'] = self.request.GET.get('mode', '')
        return ctx


class DetailPaiementView(LoginRequiredMixin, DetailView):
    model = Paiement
    template_name = 'paiements/detail_paiement.html'
    context_object_name = 'paiement'

    def get_queryset(self):
        return Paiement.objects.select_related(
            'rendez_vous__patient__user',
            'rendez_vous__medecin__user',
            'consultation__dossier__patient__user',
            'consultation__medecin__user',
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        paiement = self.object
        consultation = paiement.consultation
        if consultation:
            ctx['historique_paiements'] = Paiement.objects.filter(
                consultation=consultation
            ).exclude(pk=paiement.pk).order_by('-date_creation')
        else:
            ctx['historique_paiements'] = Paiement.objects.none()
        return ctx


class WebhookDjomyView(View):
    """Endpoint de réception des webhooks Djomy — pas de LoginRequired."""

    def post(self, request):
        from .djomy_client import DjomyClient
        signature = request.headers.get('X-Djomy-Signature', '')
        try:
            client = DjomyClient()
            data = client.traiter_webhook(request.body, signature)
            reference = data.get('reference', '')
            statut = data.get('status', '')
            if reference:
                mapping = {
                    'success': 'confirme',
                    'failed': 'echoue',
                    'pending': 'initie',
                }
                Paiement.objects.filter(reference_interne=reference).update(
                    statut_paiement=mapping.get(statut, 'en_attente'),
                    reference_djomy=data.get('transaction_id', ''),
                    webhook_payload=data,
                )
            return JsonResponse({'status': 'ok'})
        except ValueError:
            return JsonResponse({'error': 'Signature invalide'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
