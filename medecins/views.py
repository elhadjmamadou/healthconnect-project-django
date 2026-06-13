# ==============================================================================
# medecins/views.py — Vues de gestion des médecins et de l'annuaire public
# ==============================================================================
# Ce fichier contient deux types de vues :
#
# VUES PUBLIQUES (sans authentification requise) :
#   AnnuaireView       : liste tous les médecins actifs avec recherche et filtres
#   AnnuaireDetailView : profil complet d'un médecin avec ses disponibilités
#
# VUES PROTÉGÉES (réservées aux admins et médecins) :
#   DashboardMedecinView : tableau de bord du médecin connecté
#   ListeMedecinsView    : liste admin des médecins avec filtres avancés
#   DetailMedecinView    : fiche complète d'un médecin (lecture)
#   CreerMedecinView     : formulaire de création (admin seulement)
#   ModifierMedecinView  : formulaire de modification (admin seulement)
#   SupprimerMedecinView : suppression (admin seulement)
#   ListeSpecialitesView : gestion des spécialités médicales
#   CreerSpecialiteView  : ajout d'une spécialité
#   SupprimerSpecialiteView : suppression d'une spécialité
# ==============================================================================

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


class AnnuaireView(ListView):
    """
    Annuaire public des médecins — accessible sans compte utilisateur.

    Hérite de ListView (vue générique Django) qui gère automatiquement :
      - la pagination (paginate_by = 12 médecins par page)
      - le queryset et son passage au template (context_object_name)
      - la gestion des pages vides

    Filtres disponibles via paramètres GET dans l'URL :
      ?q=mamadou        → recherche par nom ou spécialité
      ?specialite=3     → filtre par ID de spécialité
      ?page=2           → deuxième page des résultats
    """

    model = Medecin
    template_name = 'medecins/annuaire.html'
    context_object_name = 'medecins'
    paginate_by = 12

    def get_queryset(self):
        """
        Construit le queryset des médecins selon les filtres de recherche.

        Optimisations :
          select_related('user') : JOIN SQL sur la table users → un seul aller-retour
          prefetch_related('specialites') : requête séparée pour les M2M → évite N+1
          filter(user__statut='actif') : seuls les comptes actifs sont visibles
          distinct() : nécessaire après le filtre OR sur spécialites (évite les doublons)
        """
        qs = (
            Medecin.objects.select_related('user')
            .prefetch_related('specialites')
            .filter(user__statut='actif')
            .order_by('user__last_name', 'user__first_name')
        )

        q    = self.request.GET.get('q', '').strip()
        spec = self.request.GET.get('specialite', '')

        if q:
            # Q() permet de combiner des conditions avec OR (|)
            # icontains : insensible à la casse (ILIKE en SQL)
            qs = qs.filter(
                Q(user__first_name__icontains=q)
                | Q(user__last_name__icontains=q)
                | Q(specialites__libelle__icontains=q)
            ).distinct()  # évite les doublons quand un médecin a plusieurs spécialités correspondantes

        if spec:
            # Filtre par ID de spécialité (valeur du <select> dans le formulaire)
            qs = qs.filter(specialites__id=spec)

        return qs

    def get_context_data(self, **kwargs):
        """Ajoute au contexte les données nécessaires au formulaire de recherche."""
        ctx = super().get_context_data(**kwargs)
        ctx['specialites']    = Specialite.objects.order_by('libelle')  # pour le <select>
        ctx['q']              = self.request.GET.get('q', '')           # valeur du champ texte
        ctx['spec_filter']    = self.request.GET.get('specialite', '')  # spécialité sélectionnée
        ctx['total_medecins'] = self.get_queryset().count()             # affiché dans le bandeau
        return ctx


class AnnuaireDetailView(DetailView):
    """
    Profil public d'un médecin avec ses prochaines disponibilités.

    Accessible sans compte. Affiche :
      - Identité, spécialités, numéro d'ordre, biographie
      - Tarif de consultation
      - Les 6 prochains créneaux libres
      - Bouton "Prendre rendez-vous" (redirige vers le flux de réservation)
    """

    model = Medecin
    template_name = 'medecins/annuaire_detail.html'
    context_object_name = 'medecin'

    def get_queryset(self):
        """Seuls les médecins actifs sont visibles publiquement."""
        return (
            Medecin.objects.select_related('user')
            .prefetch_related('specialites')
            .filter(user__statut='actif')
        )

    def get_context_data(self, **kwargs):
        """Ajoute les prochains créneaux disponibles au contexte."""
        from disponibilites.models import Disponibilite
        ctx = super().get_context_data(**kwargs)

        # On ne montre que les créneaux futurs et libres (statut = LIBRE)
        # Limité aux 6 prochains pour garder la page concise
        ctx['prochaines_dispos'] = Disponibilite.objects.filter(
            medecin=self.object,
            date_disponibilite__gte=timezone.localdate(),   # à partir d'aujourd'hui
            statut_creneau=Disponibilite.StatutCreneau.LIBRE,
        ).order_by('date_disponibilite', 'heure_debut')[:6]

        return ctx


class DashboardMedecinView(MedecinRequiredMixin, TemplateView):
    """
    Tableau de bord du médecin connecté.

    MedecinRequiredMixin garantit :
      1. Utilisateur connecté (sinon → login)
      2. Rôle = MEDECIN (sinon → 403)

    Affiche :
      - RDV du jour
      - Stats : nb RDV aujourd'hui, patients du mois, total consultations
      - Prochains RDV (5 suivants)
      - Consultations récentes (5 dernières)
    """

    template_name = 'medecins/dashboard_medecin.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from rendez_vous.models import RendezVous
        from consultations.models import Consultation

        # Accès au profil médecin depuis le User connecté
        medecin = self.request.user.medecin_profile
        today       = timezone.localdate()
        month_start = today.replace(day=1)

        ctx['medecin'] = medecin
        ctx['today']   = today

        # RDV du jour dans l'ordre chronologique pour l'agenda
        ctx['rdv_today'] = RendezVous.objects.filter(
            medecin=medecin, date_rdv=today
        ).select_related('patient__user').order_by('heure_debut')

        ctx['stats'] = {
            # Nombre de RDV aujourd'hui
            'rdv_today_count': RendezVous.objects.filter(medecin=medecin, date_rdv=today).count(),
            # Patients uniques ayant eu un RDV ce mois-ci
            # values('patient').distinct() : compte les patients différents, pas les RDV
            'patients_mois': RendezVous.objects.filter(
                medecin=medecin, date_rdv__gte=month_start
            ).values('patient').distinct().count(),
            # Total de toutes les consultations pour ce médecin (toute la période)
            'consultations_total': Consultation.objects.filter(medecin=medecin).count(),
        }

        # Prochains RDV actifs (en attente ou confirmés), limités à 5
        ctx['prochains_rdv'] = RendezVous.objects.filter(
            medecin=medecin,
            date_rdv__gte=today,
            statut_rdv__in=['en_attente', 'confirme'],
        ).select_related('patient__user').order_by('date_rdv', 'heure_debut')[:5]

        # Consultations récentes pour la section "Historique"
        ctx['consultations_recentes'] = Consultation.objects.filter(
            medecin=medecin
        ).select_related('dossier__patient__user').order_by('-date_consultation')[:5]

        return ctx


class ListeMedecinsView(LoginRequiredMixin, ListView):
    """
    Liste interne des médecins avec filtres avancés (admin/staff).

    annotate(nb_rdv=Count('rendez_vous')) : ajoute un attribut calculé
    nb_rdv à chaque objet Medecin pour l'afficher dans la liste.
    """

    model = Medecin
    template_name = 'medecins/liste_medecins.html'
    context_object_name = 'medecins'
    paginate_by = 12

    def get_queryset(self):
        qs = Medecin.objects.select_related('user').prefetch_related('specialites').annotate(
            nb_rdv=Count('rendez_vous')   # champ calculé : nombre total de RDV
        )
        q         = self.request.GET.get('q', '')
        specialite = self.request.GET.get('specialite', '')
        statut    = self.request.GET.get('statut', '')

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
        ctx['specialites']         = Specialite.objects.all()
        ctx['q']                   = self.request.GET.get('q', '')
        ctx['selected_specialite'] = self.request.GET.get('specialite', '')
        ctx['selected_statut']     = self.request.GET.get('statut', '')
        return ctx


class DetailMedecinView(LoginRequiredMixin, DetailView):
    """Fiche complète d'un médecin (lecture seule — accès connectés)."""
    model = Medecin
    template_name = 'medecins/detail_medecin.html'
    context_object_name = 'medecin'


class CreerMedecinView(AdminRequiredMixin, View):
    """
    Formulaire de création d'un nouveau médecin (admin seulement).

    Deux formulaires imbriqués :
      - user_form    : données du compte (email, prénom, nom, mot de passe)
      - profile_form : données professionnelles (numéro d'ordre, tarif, spécialités)

    @transaction.atomic garantit que si l'une des deux sauvegardes échoue,
    l'autre est annulée. On ne peut pas créer un User sans le Medecin associé.
    """

    template_name = 'medecins/creer_medecin.html'

    def get(self, request):
        return render(request, self.template_name, {
            'user_form':    CreerMedecinUserForm(),
            'profile_form': MedecinProfileForm(),
        })

    @transaction.atomic
    def post(self, request):
        user_form    = CreerMedecinUserForm(request.POST)
        profile_form = MedecinProfileForm(request.POST)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()   # crée le User avec rôle MEDECIN

            # commit=False : on diffère la sauvegarde pour attacher le User d'abord
            medecin = profile_form.save(commit=False)
            medecin.user = user
            medecin.save()

            # save_m2m() est nécessaire après commit=False pour sauvegarder
            # la relation ManyToMany (spécialités du médecin)
            profile_form.save_m2m()

            messages.success(request, f'Médecin Dr. {user.get_full_name()} créé avec succès.')
            return redirect('medecins:detail', pk=medecin.pk)

        return render(request, self.template_name, {
            'user_form':    user_form,
            'profile_form': profile_form,
        })


class ModifierMedecinView(AdminRequiredMixin, View):
    """Formulaire de modification d'un médecin existant (admin seulement)."""

    template_name = 'medecins/modifier_medecin.html'

    def _get_medecin(self, pk):
        """Récupère le médecin avec ses relations préchargées, ou lève une 404."""
        return get_object_or_404(
            Medecin.objects.select_related('user').prefetch_related('specialites'), pk=pk
        )

    def get(self, request, pk):
        medecin = self._get_medecin(pk)
        return render(request, self.template_name, {
            'medecin':      medecin,
            # instance= : pré-remplit les formulaires avec les données existantes
            'user_form':    ModifierMedecinUserForm(instance=medecin.user),
            'profile_form': MedecinProfileForm(instance=medecin),
        })

    @transaction.atomic
    def post(self, request, pk):
        medecin      = self._get_medecin(pk)
        user_form    = ModifierMedecinUserForm(request.POST, instance=medecin.user)
        profile_form = MedecinProfileForm(request.POST, instance=medecin)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Médecin modifié avec succès.')
            return redirect('medecins:detail', pk=medecin.pk)
        return render(request, self.template_name, {
            'medecin':      medecin,
            'user_form':    user_form,
            'profile_form': profile_form,
        })


class SupprimerMedecinView(AdminRequiredMixin, View):
    """
    Suppression d'un médecin (admin seulement).

    On supprime le User → CASCADE supprime automatiquement le Medecin
    (et les RDV si CASCADE est configuré sur le ForeignKey).
    """

    def post(self, request, pk):
        medecin = get_object_or_404(Medecin.objects.select_related('user'), pk=pk)
        nom = medecin.nom_complet
        medecin.user.delete()   # cascade → supprime aussi le Medecin
        messages.success(request, f'Médecin Dr. {nom} supprimé.')
        return redirect('medecins:liste')


class ListeSpecialitesView(AdminRequiredMixin, ListView):
    """
    Liste des spécialités médicales (admin seulement).

    annotate(nb_medecins=Count('medecins')) : nombre de médecins par spécialité.
    Le formulaire de création est intégré sur la même page.
    """

    model = Specialite
    template_name = 'medecins/specialites.html'
    context_object_name = 'specialites'

    def get_queryset(self):
        # Annotate ajoute le champ calculé nb_medecins à chaque Specialite
        return Specialite.objects.annotate(nb_medecins=Count('medecins')).order_by('libelle')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = SpecialiteForm()   # formulaire vide pour l'ajout rapide
        return ctx


class CreerSpecialiteView(AdminRequiredMixin, View):
    """Traitement du formulaire POST d'ajout de spécialité."""

    def post(self, request):
        form = SpecialiteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Spécialité ajoutée.')
        else:
            # Affichage des erreurs de validation (ex : libellé déjà existant)
            for errors in form.errors.values():
                for error in errors:
                    messages.error(request, error)
        return redirect('medecins:specialites')


class SupprimerSpecialiteView(AdminRequiredMixin, View):
    """Suppression d'une spécialité médicale."""

    def post(self, request, pk):
        spec = get_object_or_404(Specialite, pk=pk)
        libelle = spec.libelle
        spec.delete()
        messages.success(request, f'Spécialité "{libelle}" supprimée.')
        return redirect('medecins:specialites')
