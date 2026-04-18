from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import ListView

from users.mixins import PatientRequiredMixin
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
            canal = request.POST.get('canal', 'plateforme')

            try:
                dispo = Disponibilite.objects.get(pk=dispo_id, statut_creneau='libre')
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
                    statut_rdv='en_attente',
                )
                request.session.pop('rdv_medecin_id', None)
                request.session.pop('rdv_dispo_id', None)
                messages.success(request, 'Votre rendez-vous a été enregistré avec succès !')
                return redirect('rendez_vous:liste')
            except Disponibilite.DoesNotExist:
                messages.error(request, 'Ce créneau n\'est plus disponible.')
                return redirect(f"{request.path}?step=2")

        return redirect(f"{request.path}?step=1")


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


class AnnulerRDVView(LoginRequiredMixin, View):
    def post(self, request, pk):
        rdv = RendezVous.objects.get(pk=pk)
        if rdv.est_annulable:
            if request.user.is_patient:
                rdv.statut_rdv = 'annule_patient'
            else:
                rdv.statut_rdv = 'annule_medecin'
            rdv.save()
            messages.success(request, 'Rendez-vous annulé.')
        return redirect('rendez_vous:liste')
