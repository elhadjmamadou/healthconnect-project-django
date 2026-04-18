from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, ListView

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
