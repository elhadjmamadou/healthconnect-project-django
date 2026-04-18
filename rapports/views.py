from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Sum
from django.utils import timezone
from django.views.generic import TemplateView

from users.mixins import AdminRequiredMixin


class DashboardAdminView(AdminRequiredMixin, TemplateView):
    template_name = 'rapports/dashboard_admin.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from patients.models import Patient
        from medecins.models import Medecin, Specialite
        from rendez_vous.models import RendezVous
        from paiements.models import Paiement
        from notifications.models import Notification

        today = timezone.localdate()
        month_start = today.replace(day=1)

        # Stats
        ctx['stats'] = {
            'total_patients': Patient.objects.count(),
            'total_medecins': Medecin.objects.count(),
            'rdv_today': RendezVous.objects.filter(date_rdv=today).count(),
            'revenus_mois': Paiement.objects.filter(
                statut_paiement='confirme',
                date_paiement__date__gte=month_start,
            ).aggregate(total=Sum('montant'))['total'] or 0,
            'patients_new_month': Patient.objects.filter(date_creation__date__gte=month_start).count(),
        }

        # RDV récents
        ctx['rdv_recents'] = RendezVous.objects.select_related(
            'patient__user', 'medecin__user'
        ).order_by('-date_rdv', '-heure_debut')[:6]

        # Top médecins
        medecins = Medecin.objects.annotate(
            nb_rdv=Count('rendez_vous')
        ).order_by('-nb_rdv')[:5]
        max_rdv = medecins.first().nb_rdv if medecins else 1
        for m in medecins:
            m.pct = int((m.nb_rdv / max(max_rdv, 1)) * 100)
        ctx['top_medecins'] = medecins

        # Chart RDV 7 derniers jours
        labels, values = [], []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            count = RendezVous.objects.filter(date_rdv=d).count()
            labels.append(d.strftime('%d/%m'))
            values.append(count)
        ctx['rdv_chart_data'] = {'labels': labels, 'values': values}

        # Chart spécialités
        specs = Specialite.objects.annotate(nb=Count('medecins')).order_by('-nb')[:5]
        ctx['specialites_chart_data'] = {
            'labels': [s.libelle for s in specs],
            'values': [s.nb for s in specs],
        }

        # Notifications récentes
        ctx['notifications_recentes'] = Notification.objects.select_related(
            'utilisateur'
        ).order_by('-date_envoi')[:5]

        return ctx


class AnalytiquesView(AdminRequiredMixin, TemplateView):
    template_name = 'rapports/analytiques.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from rendez_vous.models import RendezVous
        from paiements.models import Paiement
        from patients.models import Patient
        from medecins.models import Medecin

        today = timezone.localdate()
        periode = self.request.GET.get('periode', '30j')
        jours = {'7j': 7, '30j': 30, '3m': 90, '6m': 180, '1an': 365}.get(periode, 30)
        debut = today - timedelta(days=jours)

        # RDV evolution
        rdv_labels, rdv_values = [], []
        step = max(1, jours // 14)
        d = debut
        while d <= today:
            rdv_labels.append(d.strftime('%d/%m'))
            rdv_values.append(RendezVous.objects.filter(date_rdv=d).count())
            d += timedelta(days=step)
        ctx['rdv_chart_data'] = {'labels': rdv_labels, 'values': rdv_values}

        # Revenus mensuels (12 derniers mois)
        rev_labels, rev_values = [], []
        for i in range(11, -1, -1):
            m = (today.month - i - 1) % 12 + 1
            y = today.year - ((today.month - i - 1) // 12)
            total = Paiement.objects.filter(
                statut_paiement='confirme',
                date_paiement__year=y,
                date_paiement__month=m,
            ).aggregate(t=Sum('montant'))['t'] or 0
            rev_labels.append(f'{m:02d}/{y}')
            rev_values.append(float(total))
        ctx['revenus_chart_data'] = {'labels': rev_labels, 'values': rev_values}

        from medecins.models import Specialite
        from django.db.models import Count
        specs = Specialite.objects.annotate(nb=Count('medecins')).order_by('-nb')[:6]
        ctx['specialites_chart_data'] = {
            'labels': [s.libelle for s in specs],
            'values': [s.nb for s in specs],
        }

        # Nouveaux patients
        pt_labels, pt_values = [], []
        for i in range(11, -1, -1):
            m = (today.month - i - 1) % 12 + 1
            y = today.year - ((today.month - i - 1) // 12)
            count = Patient.objects.filter(date_creation__year=y, date_creation__month=m).count()
            pt_labels.append(f'{m:02d}/{y}')
            pt_values.append(count)
        ctx['patients_chart_data'] = {'labels': pt_labels, 'values': pt_values}

        # Stats médecins
        ctx['stats_medecins'] = Medecin.objects.annotate(
            nb_rdv=Count('rendez_vous')
        ).select_related('user').order_by('-nb_rdv')[:10]

        ctx['periode'] = periode
        ctx['periodes'] = ['7j', '30j', '3m', '6m', '1an']
        return ctx
