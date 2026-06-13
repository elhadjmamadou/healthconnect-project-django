# ==============================================================================
# rendez_vous/views.py — Vues de réservation et de gestion des rendez-vous
# ==============================================================================
# Ce fichier implémente le flux complet de réservation en 3 étapes :
#   Étape 1 : Choisir un médecin (liste avec recherche)
#   Étape 2 : Choisir un créneau de disponibilité
#   Étape 3 : Confirmer le rendez-vous (motif + canal)
#
# Le flux peut démarrer depuis l'annuaire public avec un médecin pré-sélectionné
# (URL : /rendez_vous/reserver/?medecin=42 → passe directement à l'étape 2).
# Le médecin choisi est mémorisé en SESSION Django entre les étapes.
#
# Autres vues :
#   ConfirmerRDVView : le médecin accepte le RDV → statut EN_ATTENTE → CONFIRME
#   RefuserRDVView   : le médecin refuse → statut → ANNULE_MEDECIN
#   AnnulerRDVView   : le patient ou médecin annule
#   DetailRDVView    : fiche détaillée du RDV avec section paiement
#   ListeRDVView     : liste des RDV de l'utilisateur connecté
# ==============================================================================

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
    """
    Formulaire de réservation d'un RDV en 3 étapes.

    PatientRequiredMixin → seuls les patients peuvent réserver.
    L'état entre les étapes est conservé dans la SESSION Django
    (stockage côté serveur, identifié par un cookie de session navigateur).

    GET  : affiche l'étape courante
    POST : traite l'action (select_medecin / select_dispo / confirmer)
    """

    template_name = 'rendez_vous/reservation_rdv.html'

    def get(self, request):
        """
        Affiche l'étape courante du formulaire de réservation.

        Paramètre GET ?medecin=<id> :
          Arrivée depuis l'annuaire public avec un médecin pré-sélectionné.
          On sauvegarde l'ID en session et on redirige vers l'étape 2.
          Cette mécanique permet au flux annuaire → login → réservation de
          fonctionner même si l'utilisateur n'est pas encore connecté
          (la session persiste à travers la page de login).
        """
        medecin_param = request.GET.get('medecin', '')
        if medecin_param.isdigit():
            # Sauvegarde du choix en session pour le retrouver après le login
            request.session['rdv_medecin_id'] = medecin_param
            return redirect(f"{request.path}?step=2")

        step = int(request.GET.get('step', 1))
        specialites = Specialite.objects.all()

        # Récupération des choix mémorisés en session
        medecin_id = request.session.get('rdv_medecin_id')
        medecin     = None
        disponibilites = []

        # Recherche et filtres pour la liste des médecins (étape 1)
        q           = request.GET.get('q', '')
        spec_filter = request.GET.get('specialite', '')
        medecins = Medecin.objects.select_related('user').prefetch_related('specialites').filter(
            accepte_nouveaux_patients=True   # n'afficher que les médecins disponibles
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
                # Créneaux futurs et libres pour ce médecin
                disponibilites = Disponibilite.objects.filter(
                    medecin=medecin,
                    date_disponibilite__gte=today,
                    statut_creneau='libre',
                ).order_by('date_disponibilite', 'heure_debut')
            except Medecin.DoesNotExist:
                step = 1  # médecin inexistant → retour à l'étape 1

        dispo_id = request.session.get('rdv_dispo_id')
        dispo = None
        if step == 3 and dispo_id:
            try:
                dispo   = Disponibilite.objects.select_related('medecin__user').get(pk=dispo_id)
                medecin = dispo.medecin
            except Disponibilite.DoesNotExist:
                step = 2  # créneau inexistant → retour à l'étape 2

        return render(request, self.template_name, {
            'step':          step,
            'specialites':   specialites,
            'medecins':      medecins,
            'medecin':       medecin,
            'disponibilites': disponibilites,
            'dispo':         dispo,
            'q':             q,
            'spec_filter':   spec_filter,
            'canal_options': RendezVous.Canal.choices,
        })

    def post(self, request):
        """
        Traite les actions POST des différentes étapes.

        action = 'select_medecin' : étape 1 → mémorise le médecin choisi
        action = 'select_dispo'   : étape 2 → mémorise le créneau choisi
        action = 'confirmer'      : étape 3 → crée le RendezVous en base
        """
        action = request.POST.get('action', '')

        if action == 'select_medecin':
            # Mémorisation du médecin en session, passage à l'étape 2
            medecin_id = request.POST.get('medecin_id')
            request.session['rdv_medecin_id'] = medecin_id
            return redirect(f"{request.path}?step=2")

        elif action == 'select_dispo':
            # Mémorisation du créneau en session, passage à l'étape 3
            dispo_id = request.POST.get('dispo_id')
            request.session['rdv_dispo_id'] = dispo_id
            return redirect(f"{request.path}?step=3")

        elif action == 'confirmer':
            dispo_id = request.session.get('rdv_dispo_id')
            motif = request.POST.get('motif', '')
            canal = request.POST.get('canal', RendezVous.Canal.PLATEFORME)

            try:
                # Double vérification : le créneau est encore libre au moment de la confirmation
                # (quelqu'un d'autre aurait pu le réserver entre l'étape 2 et la confirmation)
                dispo   = Disponibilite.objects.get(pk=dispo_id, statut_creneau=Disponibilite.StatutCreneau.LIBRE)
                patient = request.user.patient_profile

                # Création du RDV avec toutes les données du créneau
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
                # Nettoyage de la session après la réservation
                request.session.pop('rdv_medecin_id', None)
                request.session.pop('rdv_dispo_id', None)

                # Le signal post_save dans notifications/signals.py notifie automatiquement le médecin
                messages.success(request, 'Votre rendez-vous a été enregistré avec succès !')
                return redirect('rendez_vous:liste')

            except Disponibilite.DoesNotExist:
                # Créneau pris entre temps → retour à la sélection de créneau
                messages.error(request, 'Ce créneau n\'est plus disponible.')
                return redirect(f"{request.path}?step=2")

        return redirect(f"{request.path}?step=1")


class RendezVousAccessMixin(LoginRequiredMixin):
    """
    Mixin de contrôle d'accès aux détails d'un RDV.

    Un RDV est visible par :
      - Le médecin dont c'est le RDV
      - Le patient dont c'est le RDV
      - (Les admins gèrent via l'admin Django directement)

    Toute autre tentative d'accès lève PermissionDenied (→ 403).
    Ce mixin est utilisé par DetailRDVView.
    """

    def get_object(self):
        rdv  = get_object_or_404(
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
    """
    Fiche détaillée d'un rendez-vous.

    Affiche les informations du patient, du médecin, les horaires,
    le statut et la section paiement (bouton "Payer" ou badge "Payé").

    get_context_data() tente d'accéder à rdv.paiement (OneToOneField).
    Si aucun paiement n'est lié, ObjectDoesNotExist est levée → on passe None.
    """

    model = RendezVous
    template_name = 'rendez_vous/detail_rdv.html'
    context_object_name = 'rdv'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['paiement'] = self.object.paiement  # OneToOneField → peut lever DoesNotExist
        except ObjectDoesNotExist:
            context['paiement'] = None  # pas de paiement lié → bouton "Payer" affiché
        return context


class ConfirmerRDVView(MedecinRequiredMixin, View):
    """
    Le médecin confirme un rendez-vous en attente.

    Seul le médecin propriétaire du RDV peut confirmer.
    Après confirmation, le signal notifications/signals.py envoie
    automatiquement une notification au patient.
    """

    def post(self, request, pk):
        rdv = get_object_or_404(
            RendezVous.objects.select_related('medecin__user'),
            pk=pk,
        )
        # Vérification que c'est bien le RDV du médecin connecté
        if rdv.medecin.user != request.user:
            raise PermissionDenied

        if rdv.statut_rdv == RendezVous.StatutRdv.EN_ATTENTE:
            rdv.statut_rdv = RendezVous.StatutRdv.CONFIRME
            rdv.save()  # déclenche le signal → notification patient
            messages.success(request, 'Rendez-vous confirmé.')
        else:
            messages.warning(request, 'Ce rendez-vous ne peut pas être confirmé.')

        return redirect('rendez_vous:detail', pk=rdv.pk)


class RefuserRDVView(MedecinRequiredMixin, View):
    """
    Le médecin refuse/annule un rendez-vous en attente.

    Statut → ANNULE_MEDECIN : déclenche le signal notifications/signals.py
    qui notifie le patient de l'annulation par le médecin.
    """

    def post(self, request, pk):
        rdv = get_object_or_404(
            RendezVous.objects.select_related('medecin__user'),
            pk=pk,
        )
        if rdv.medecin.user != request.user:
            raise PermissionDenied

        if rdv.statut_rdv == RendezVous.StatutRdv.EN_ATTENTE:
            rdv.statut_rdv = RendezVous.StatutRdv.ANNULE_MEDECIN
            rdv.save()  # déclenche le signal → notification patient
            messages.success(request, 'Rendez-vous refusé par le médecin.')
        else:
            messages.warning(request, 'Ce rendez-vous ne peut pas être refusé.')

        return redirect('rendez_vous:detail', pk=rdv.pk)


class AnnulerRDVView(LoginRequiredMixin, View):
    """
    Annulation d'un rendez-vous par le patient ou le médecin.

    La propriété est_annulable (définie dans le modèle RendezVous) détermine
    si l'annulation est encore possible (seulement si EN_ATTENTE ou CONFIRME).

    Selon qui annule :
      - Patient → statut = ANNULE_PATIENT → notification au médecin
      - Médecin → statut = ANNULE_MEDECIN → notification au patient
    """

    def post(self, request, pk):
        rdv = get_object_or_404(
            RendezVous.objects.select_related('patient__user', 'medecin__user'),
            pk=pk,
        )
        user = request.user

        # Vérifie que le statut permet encore l'annulation
        if not rdv.est_annulable:
            messages.error(request, 'Ce rendez-vous ne peut plus être annulé.')
            return redirect('rendez_vous:detail', pk=rdv.pk)

        # Détermine le statut d'annulation selon le rôle de l'utilisateur
        if user.is_patient and rdv.patient.user == user:
            rdv.statut_rdv = RendezVous.StatutRdv.ANNULE_PATIENT
        elif user.is_medecin and rdv.medecin.user == user:
            rdv.statut_rdv = RendezVous.StatutRdv.ANNULE_MEDECIN
        else:
            raise PermissionDenied  # ni patient ni médecin du RDV → 403

        rdv.save()  # déclenche le signal → notification à l'autre partie
        messages.success(request, 'Rendez-vous annulé.')
        return redirect('rendez_vous:liste')


class ListeRDVView(LoginRequiredMixin, ListView):
    """
    Liste des rendez-vous de l'utilisateur connecté.

    Filtrage par rôle :
      - Patient : ses propres RDV
      - Médecin  : les RDV de son agenda
      - Admin    : sans filtre (tous les RDV) — accès via l'admin Django
    """

    model = RendezVous
    template_name = 'rendez_vous/liste_rdv.html'
    context_object_name = 'rendez_vous_list'
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        qs   = RendezVous.objects.select_related('patient__user', 'medecin__user')

        if user.is_patient:
            qs = qs.filter(patient__user=user)
        elif user.is_medecin:
            qs = qs.filter(medecin__user=user)

        # Tri antichronologique : les plus récents en premier
        return qs.order_by('-date_rdv', '-heure_debut')
