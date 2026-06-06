from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from users.mixins import AdminRequiredMixin, MedecinRequiredMixin

from .forms import CreerMedecinUserForm, MedecinProfileForm, ModifierMedecinUserForm, SpecialiteForm
from .models import Medecin, Specialite


class DashboardMedecinView(MedecinRequiredMixin, TemplateView):
    template_name = 'medecins/dashboard_medecin.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from rendez_vous.models import RendezVous
        from consultations.models import Consultation

        medecin = self.request.user.medecin_profile
        today = timezone.localdate()
        month_start = today.replace(day=1)

        ctx['medecin'] = medecin
        ctx['today'] = today
        ctx['rdv_today'] = RendezVous.objects.filter(
            medecin=medecin, date_rdv=today
        ).select_related('patient__user').order_by('heure_debut')

        ctx['stats'] = {
            'rdv_today_count': RendezVous.objects.filter(medecin=medecin, date_rdv=today).count(),
            'patients_mois': RendezVous.objects.filter(
                medecin=medecin, date_rdv__gte=month_start
            ).values('patient').distinct().count(),
            'consultations_total': Consultation.objects.filter(medecin=medecin).count(),
        }

        ctx['prochains_rdv'] = RendezVous.objects.filter(
            medecin=medecin,
            date_rdv__gte=today,
            statut_rdv__in=['en_attente', 'confirme'],
        ).select_related('patient__user').order_by('date_rdv', 'heure_debut')[:5]

        ctx['consultations_recentes'] = Consultation.objects.filter(
            medecin=medecin
        ).select_related('dossier__patient__user').order_by('-date_consultation')[:5]

        return ctx


class ListeMedecinsView(LoginRequiredMixin, ListView):
    model = Medecin
    template_name = 'medecins/liste_medecins.html'
    context_object_name = 'medecins'
    paginate_by = 12

    def get_queryset(self):
        qs = Medecin.objects.select_related('user').prefetch_related('specialites').annotate(
            nb_rdv=Count('rendez_vous')
        )
        q = self.request.GET.get('q', '')
        specialite = self.request.GET.get('specialite', '')
        statut = self.request.GET.get('statut', '')

        if q:
            qs = qs.filter(
                Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q) |
                Q(numero_ordre__icontains=q) | Q(specialites__libelle__icontains=q)
            ).distinct()
        if specialite:
            qs = qs.filter(specialites__id=specialite)
        if statut == 'actif':
            qs = qs.filter(user__statut='actif')
        elif statut == 'inactif':
            qs = qs.filter(user__statut='inactif')

        return qs.order_by('user__last_name')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['specialites'] = Specialite.objects.all()
        ctx['q'] = self.request.GET.get('q', '')
        ctx['selected_specialite'] = self.request.GET.get('specialite', '')
        ctx['selected_statut'] = self.request.GET.get('statut', '')
        return ctx


class DetailMedecinView(LoginRequiredMixin, DetailView):
    model = Medecin
    template_name = 'medecins/detail_medecin.html'
    context_object_name = 'medecin'


class CreerMedecinView(AdminRequiredMixin, View):
    template_name = 'medecins/creer_medecin.html'

    def get(self, request):
        return render(request, self.template_name, {
            'user_form': CreerMedecinUserForm(),
            'profile_form': MedecinProfileForm(),
        })

    @transaction.atomic
    def post(self, request):
        user_form = CreerMedecinUserForm(request.POST)
        profile_form = MedecinProfileForm(request.POST)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            medecin = profile_form.save(commit=False)
            medecin.user = user
            medecin.save()
            profile_form.save_m2m()
            messages.success(request, f'Médecin Dr. {user.get_full_name()} créé avec succès.')
            return redirect('medecins:detail', pk=medecin.pk)
        return render(request, self.template_name, {
            'user_form': user_form,
            'profile_form': profile_form,
        })


class ModifierMedecinView(AdminRequiredMixin, View):
    template_name = 'medecins/modifier_medecin.html'

    def _get_medecin(self, pk):
        return get_object_or_404(
            Medecin.objects.select_related('user').prefetch_related('specialites'), pk=pk
        )

    def get(self, request, pk):
        medecin = self._get_medecin(pk)
        return render(request, self.template_name, {
            'medecin': medecin,
            'user_form': ModifierMedecinUserForm(instance=medecin.user),
            'profile_form': MedecinProfileForm(instance=medecin),
        })

    @transaction.atomic
    def post(self, request, pk):
        medecin = self._get_medecin(pk)
        user_form = ModifierMedecinUserForm(request.POST, instance=medecin.user)
        profile_form = MedecinProfileForm(request.POST, instance=medecin)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Médecin modifié avec succès.')
            return redirect('medecins:detail', pk=medecin.pk)
        return render(request, self.template_name, {
            'medecin': medecin,
            'user_form': user_form,
            'profile_form': profile_form,
        })


class SupprimerMedecinView(AdminRequiredMixin, View):
    def post(self, request, pk):
        medecin = get_object_or_404(Medecin.objects.select_related('user'), pk=pk)
        nom = medecin.nom_complet
        medecin.user.delete()
        messages.success(request, f'Médecin Dr. {nom} supprimé.')
        return redirect('medecins:liste')


class ListeSpecialitesView(AdminRequiredMixin, ListView):
    model = Specialite
    template_name = 'medecins/specialites.html'
    context_object_name = 'specialites'

    def get_queryset(self):
        return Specialite.objects.annotate(nb_medecins=Count('medecins')).order_by('libelle')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = SpecialiteForm()
        return ctx


class CreerSpecialiteView(AdminRequiredMixin, View):
    def post(self, request):
        form = SpecialiteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Spécialité ajoutée.')
        else:
            for errors in form.errors.values():
                for error in errors:
                    messages.error(request, error)
        return redirect('medecins:specialites')


class SupprimerSpecialiteView(AdminRequiredMixin, View):
    def post(self, request, pk):
        spec = get_object_or_404(Specialite, pk=pk)
        libelle = spec.libelle
        spec.delete()
        messages.success(request, f'Spécialité "{libelle}" supprimée.')
        return redirect('medecins:specialites')
