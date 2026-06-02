from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from users.mixins import AdminRequiredMixin, MedecinRequiredMixin
from rendez_vous.models import RendezVous

from .forms import ConsultationForm
from .models import Consultation, DossierMedical


class DossierMedicalView(LoginRequiredMixin, DetailView):
    model = DossierMedical
    template_name = 'consultations/dossier_medical.html'
    context_object_name = 'dossier'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['consultations'] = self.object.consultations.select_related(
            'medecin__user'
        ).order_by('-date_consultation')
        return ctx


class ListeConsultationsView(LoginRequiredMixin, ListView):
    model = Consultation
    template_name = 'consultations/liste_consultations.html'
    context_object_name = 'consultations'
    paginate_by = 20

    def get_queryset(self):
        return Consultation.objects.select_related(
            'dossier__patient__user', 'medecin__user'
        ).order_by('-date_consultation')


class CreerConsultationView(MedecinRequiredMixin, SuccessMessageMixin, CreateView):
    """Vue pour créer une consultation liée à un rendez-vous."""
    model = Consultation
    form_class = ConsultationForm
    template_name = 'consultations/creer_consultation.html'
    success_message = 'Consultation créée avec succès.'

    def dispatch(self, request, *args, **kwargs):
        """Vérifier que le RDV existe et appartient au médecin."""
        self.rdv = get_object_or_404(RendezVous, pk=kwargs['rdv_pk'])
        if self.rdv.medecin != request.user.medecin_profile:
            raise Http404("Vous n'avez pas accès à ce rendez-vous.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['rdv'] = self.rdv
        ctx['patient'] = self.rdv.patient
        ctx['dossier'] = self.rdv.patient.dossier_medical
        return ctx

    @transaction.atomic
    def form_valid(self, form):
        """Créer la consultation et marquer le RDV comme terminé."""
        consultation = form.save(commit=False)
        consultation.dossier = self.rdv.patient.dossier_medical
        consultation.medecin = self.request.user.medecin_profile
        consultation.rendez_vous = self.rdv
        consultation.date_consultation = timezone.now()
        consultation.save()

        # Marquer le RDV comme terminé
        self.rdv.statut_rdv = RendezVous.StatutRdv.TERMINE
        self.rdv.save()

        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy('consultations:detail', kwargs={'pk': self.object.pk})


class EditerConsultationView(MedecinRequiredMixin, SuccessMessageMixin, UpdateView):
    """Vue pour modifier une consultation (médecin seulement)."""
    model = Consultation
    form_class = ConsultationForm
    template_name = 'consultations/editer_consultation.html'
    success_message = 'Consultation mise à jour avec succès.'

    def get_queryset(self):
        """Filtrer pour ne montrer que les consultations du médecin."""
        return Consultation.objects.filter(medecin=self.request.user.medecin_profile)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['patient'] = self.object.dossier.patient
        ctx['dossier'] = self.object.dossier
        return ctx

    def get_success_url(self):
        return reverse_lazy('consultations:detail', kwargs={'pk': self.object.pk})


class DetailConsultationView(LoginRequiredMixin, DetailView):
    """Vue pour afficher les détails d'une consultation."""
    model = Consultation
    template_name = 'consultations/detail_consultation.html'
    context_object_name = 'consultation'

    def get_queryset(self):
        """Filtrer l'accès : patient concerné, médecin, ou admin."""
        qs = Consultation.objects.select_related(
            'dossier__patient__user', 'medecin__user', 'rendez_vous'
        )
        user = self.request.user

        if user.is_admin_role or user.is_staff:
            return qs

        if user.is_medecin:
            return qs.filter(medecin=user.medecin_profile)

        if user.is_patient:
            return qs.filter(dossier__patient__user=user)

        return qs.none()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['patient'] = self.object.dossier.patient
        ctx['dossier'] = self.object.dossier
        ctx['can_edit'] = (
            self.request.user.is_medecin and
            self.object.medecin == self.request.user.medecin_profile
        )
        return ctx
