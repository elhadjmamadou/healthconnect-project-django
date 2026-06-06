from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from users.mixins import AdminRequiredMixin, PatientRequiredMixin

from .forms import CreerPatientUserForm, ModifierPatientUserForm, PatientProfileForm
from .models import Patient


class DashboardPatientView(PatientRequiredMixin, TemplateView):
    template_name = 'patients/dashboard_patient.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from rendez_vous.models import RendezVous
        from consultations.models import Consultation

        patient = self.request.user.patient_profile
        today = timezone.localdate()
        year_start = today.replace(month=1, day=1)

        ctx['patient'] = patient

        prochain = RendezVous.objects.filter(
            patient=patient,
            date_rdv__gte=today,
            statut_rdv__in=['en_attente', 'confirme'],
        ).select_related('medecin__user').order_by('date_rdv', 'heure_debut').first()
        ctx['prochain_rdv'] = prochain

        ctx['stats'] = {
            'rdv_annee': RendezVous.objects.filter(patient=patient, date_rdv__gte=year_start).count(),
            'consultations': Consultation.objects.filter(dossier__patient=patient).count(),
        }

        ctx['consultations_recentes'] = Consultation.objects.filter(
            dossier__patient=patient
        ).select_related('medecin__user').order_by('-date_consultation')[:5]

        return ctx


class ListePatientsView(LoginRequiredMixin, ListView):
    model = Patient
    template_name = 'patients/liste_patients.html'
    context_object_name = 'patients'
    paginate_by = 15

    def get_queryset(self):
        qs = Patient.objects.select_related('user').annotate(
            nb_rdv=Count('rendez_vous')
        )
        q = self.request.GET.get('q', '')
        sexe = self.request.GET.get('sexe', '')
        statut = self.request.GET.get('statut', '')

        if q:
            qs = qs.filter(
                Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q) |
                Q(user__email__icontains=q)
            )
        if sexe:
            qs = qs.filter(sexe=sexe)
        if statut:
            qs = qs.filter(user__statut=statut)

        return qs.order_by('user__last_name')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['selected_sexe'] = self.request.GET.get('sexe', '')
        ctx['selected_statut'] = self.request.GET.get('statut', '')
        return ctx


class DetailPatientView(LoginRequiredMixin, DetailView):
    model = Patient
    template_name = 'patients/detail_patient.html'
    context_object_name = 'patient'


class CreerPatientView(AdminRequiredMixin, View):
    template_name = 'patients/creer_patient.html'

    def get(self, request):
        return render(request, self.template_name, {
            'user_form': CreerPatientUserForm(),
            'profile_form': PatientProfileForm(),
        })

    @transaction.atomic
    def post(self, request):
        user_form = CreerPatientUserForm(request.POST)
        profile_form = PatientProfileForm(request.POST)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            patient = profile_form.save(commit=False)
            patient.user = user
            patient.save()
            messages.success(request, f'Patient {user.get_full_name()} créé avec succès.')
            return redirect('patients:detail', pk=patient.pk)
        return render(request, self.template_name, {
            'user_form': user_form,
            'profile_form': profile_form,
        })


class ModifierPatientView(AdminRequiredMixin, View):
    template_name = 'patients/modifier_patient.html'

    def _get_patient(self, pk):
        return get_object_or_404(Patient.objects.select_related('user'), pk=pk)

    def get(self, request, pk):
        patient = self._get_patient(pk)
        return render(request, self.template_name, {
            'patient': patient,
            'user_form': ModifierPatientUserForm(instance=patient.user),
            'profile_form': PatientProfileForm(instance=patient),
        })

    @transaction.atomic
    def post(self, request, pk):
        patient = self._get_patient(pk)
        user_form = ModifierPatientUserForm(request.POST, instance=patient.user)
        profile_form = PatientProfileForm(request.POST, instance=patient)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Patient modifié avec succès.')
            return redirect('patients:detail', pk=patient.pk)
        return render(request, self.template_name, {
            'patient': patient,
            'user_form': user_form,
            'profile_form': profile_form,
        })


class SupprimerPatientView(AdminRequiredMixin, View):
    def post(self, request, pk):
        patient = get_object_or_404(Patient.objects.select_related('user'), pk=pk)
        nom = patient.nom_complet
        patient.user.delete()
        messages.success(request, f'Patient {nom} supprimé.')
        return redirect('patients:liste')
