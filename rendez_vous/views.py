from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView

from users.mixins import MedecinRequiredMixin, PatientRequiredMixin
from medecins.models import Medecin, Specialite
from disponibilites.models import Disponibilite
from .models import RendezVous


class ReservationRDVView(PatientRequiredMixin, View):
    template_name = 'rendez_vous/reservation_rdv.html'

    def get(self, request):
        step = int(request.GET.get('step', 1))
        specialites = Specialite.objects.all()
        medecin_id = request.session.get('rdv_medecin_id')
        medecin = None
        disponibilites = []

        q = request.GET.get('q', '')
        spec_filter = request.GET.get('specialite', '')
        medecins = Medecin.objects.select_related('user').prefetch_related('specialites').filter(
            accepte_nouveaux_patients=True
        )
        if q:
            from django.db.models import Q
            medecins = medecins.filter(
                Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q)
            )
        if spec_filter:
            medecins = medecins.filter(specialites__id=spec_filter)

        if step == 2 and medecin_id:
            try:
                medecin = Medecin.objects.get(pk=medecin_id)
                today = timezone.localdate()
                disponibilites = Disponibilite.objects.filter(
                    medecin=medecin,
                    date_disponibilite__gte=today,
                    statut_creneau='libre',
                ).order_by('date_disponibilite', 'heure_debut')
            except Medecin.DoesNotExist:
                step = 1

        dispo_id = request.session.get('rdv_dispo_id')
        dispo = None
        if step == 3 and dispo_id:
            try:
                dispo = Disponibilite.objects.select_related('medecin__user').get(pk=dispo_id)
                medecin = dispo.medecin
            except Disponibilite.DoesNotExist:
                step = 2

        return render(request, self.template_name, {
            'step': step,
            'specialites': specialites,
            'medecins': medecins,
            'medecin': medecin,
            'disponibilites': disponibilites,
            'dispo': dispo,
            'q': q,
            'spec_filter': spec_filter,
            'canal_options': RendezVous.Canal.choices,
        })

    def post(self, request):
        action = request.POST.get('action', '')

        if action == 'select_medecin':
            medecin_id = request.POST.get('medecin_id')
            request.session['rdv_medecin_id'] = medecin_id
            return redirect(f"{request.path}?step=2")

        elif action == 'select_dispo':
            dispo_id = request.POST.get('dispo_id')
            request.session['rdv_dispo_id'] = dispo_id
            return redirect(f"{request.path}?step=3")

        elif action == 'confirmer':
            dispo_id = request.session.get('rdv_dispo_id')
            motif = request.POST.get('motif', '')
            canal = request.POST.get('canal', RendezVous.Canal.PLATEFORME)

            try:
                dispo = Disponibilite.objects.get(pk=dispo_id, statut_creneau=Disponibilite.StatutCreneau.LIBRE)
                patient = request.user.patient_profile
                rdv = RendezVous.objects.create(
                    patient=patient,
                    medecin=dispo.medecin,
                    disponibilite=dispo,
                    date_rdv=dispo.date_disponibilite,
                    heure_debut=dispo.heure_debut,
                    heure_fin=dispo.heure_fin,
                    motif=motif,
                    canal=canal,
                    statut_rdv=RendezVous.StatutRdv.EN_ATTENTE,
                )
                request.session.pop('rdv_medecin_id', None)
                request.session.pop('rdv_dispo_id', None)
                messages.success(request, 'Votre rendez-vous a été enregistré avec succès !')
                return redirect('rendez_vous:liste')
            except Disponibilite.DoesNotExist:
                messages.error(request, 'Ce créneau n\'est plus disponible.')
                return redirect(f"{request.path}?step=2")

        return redirect(f"{request.path}?step=1")


class RendezVousAccessMixin(LoginRequiredMixin):
    def get_object(self):
        rdv = get_object_or_404(
            RendezVous.objects.select_related('patient__user', 'medecin__user'),
            pk=self.kwargs['pk']
        )
        user = self.request.user
        if user.is_medecin and rdv.medecin.user == user:
            return rdv
        if user.is_patient and rdv.patient.user == user:
            return rdv
        raise PermissionDenied


class DetailRDVView(RendezVousAccessMixin, DetailView):
    model = RendezVous
    template_name = 'rendez_vous/detail_rdv.html'
    context_object_name = 'rdv'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['paiement'] = self.object.paiement
        except ObjectDoesNotExist:
            context['paiement'] = None
        return context


class ConfirmerRDVView(MedecinRequiredMixin, View):
    def post(self, request, pk):
        rdv = get_object_or_404(
            RendezVous.objects.select_related('medecin__user'),
            pk=pk,
        )
        if rdv.medecin.user != request.user:
            raise PermissionDenied
        if rdv.statut_rdv == RendezVous.StatutRdv.EN_ATTENTE:
            rdv.statut_rdv = RendezVous.StatutRdv.CONFIRME
            rdv.save()
            messages.success(request, 'Rendez-vous confirmé.')
        else:
            messages.warning(request, 'Ce rendez-vous ne peut pas être confirmé.')
        return redirect('rendez_vous:detail', pk=rdv.pk)


class RefuserRDVView(MedecinRequiredMixin, View):
    def post(self, request, pk):
        rdv = get_object_or_404(
            RendezVous.objects.select_related('medecin__user'),
            pk=pk,
        )
        if rdv.medecin.user != request.user:
            raise PermissionDenied
        if rdv.statut_rdv == RendezVous.StatutRdv.EN_ATTENTE:
            rdv.statut_rdv = RendezVous.StatutRdv.ANNULE_MEDECIN
            rdv.save()
            messages.success(request, 'Rendez-vous refusé par le médecin.')
        else:
            messages.warning(request, 'Ce rendez-vous ne peut pas être refusé.')
        return redirect('rendez_vous:detail', pk=rdv.pk)


class AnnulerRDVView(LoginRequiredMixin, View):
    def post(self, request, pk):
        rdv = get_object_or_404(
            RendezVous.objects.select_related('patient__user', 'medecin__user'),
            pk=pk,
        )
        user = request.user
        if not rdv.est_annulable:
            messages.error(request, 'Ce rendez-vous ne peut plus être annulé.')
            return redirect('rendez_vous:detail', pk=rdv.pk)

        if user.is_patient and rdv.patient.user == user:
            rdv.statut_rdv = RendezVous.StatutRdv.ANNULE_PATIENT
        elif user.is_medecin and rdv.medecin.user == user:
            rdv.statut_rdv = RendezVous.StatutRdv.ANNULE_MEDECIN
        else:
            raise PermissionDenied

        rdv.save()
        messages.success(request, 'Rendez-vous annulé.')
        return redirect('rendez_vous:liste')


class ListeRDVView(LoginRequiredMixin, ListView):
    model = RendezVous
    template_name = 'rendez_vous/liste_rdv.html'
    context_object_name = 'rendez_vous_list'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        qs = RendezVous.objects.select_related('patient__user', 'medecin__user')
        if user.is_patient:
            qs = qs.filter(patient__user=user)
        elif user.is_medecin:
            qs = qs.filter(medecin__user=user)
        return qs.order_by('-date_rdv', '-heure_debut')


