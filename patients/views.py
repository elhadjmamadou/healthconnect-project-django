# ==============================================================================
# patients/views.py — Gestion des patients dans HealthConnect
# ==============================================================================
# Ce fichier contient les vues pour deux profils d'utilisateurs :
#
# PATIENT (connecté) :
#   DashboardPatientView : tableau de bord personnel avec RDV à venir et statistiques
#
# ADMIN (connecté) :
#   ListePatientsView    : liste paginée avec recherche et filtres
#   DetailPatientView    : fiche complète d'un patient
#   CreerPatientView     : création d'un compte patient (User + profil Patient)
#   ModifierPatientView  : modification du compte et du profil
#   SupprimerPatientView : suppression en cascade via patient.user.delete()
#
# Séparation des accès via les mixins :
#   PatientRequiredMixin → seuls les patients accèdent à LEUR dashboard
#   AdminRequiredMixin   → seuls les admins gèrent les comptes patients
# ==============================================================================

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
    """
    Tableau de bord personnel du patient connecté.

    PatientRequiredMixin : seuls les utilisateurs avec role=PATIENT accèdent ici.

    Données calculées à la volée :
      - prochain_rdv : premier RDV futur confirmé (ORDER BY date ASC LIMIT 1)
      - stats.rdv_annee : nombre de RDV depuis le 1er janvier de l'année en cours
      - stats.consultations : nombre total de consultations du patient
      - consultations_recentes : les 5 dernières consultations (pour l'historique)

    Imports locaux dans get_context_data() : évitent les imports circulaires
    (patients → rendez_vous → patients) au niveau module.
    """

    template_name = 'patients/dashboard_patient.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # Imports locaux pour éviter les imports circulaires entre apps
        from rendez_vous.models import RendezVous
        from consultations.models import Consultation

        patient = self.request.user.patient_profile  # accès via OneToOneField
        today = timezone.localdate()                  # date locale (Africa/Conakry)
        year_start = today.replace(month=1, day=1)    # 1er janvier de l'année en cours

        ctx['patient'] = patient

        # Premier RDV futur en attente ou confirmé (LIMIT 1 via .first())
        prochain = RendezVous.objects.filter(
            patient=patient,
            date_rdv__gte=today,
            statut_rdv__in=['en_attente', 'confirme'],
        ).select_related('medecin__user').order_by('date_rdv', 'heure_debut').first()
        ctx['prochain_rdv'] = prochain

        # Statistiques rapides : compteurs SQL (pas de chargement d'objets)
        ctx['stats'] = {
            'rdv_annee': RendezVous.objects.filter(
                patient=patient,
                date_rdv__gte=year_start  # depuis le 1er janvier
            ).count(),
            'consultations': Consultation.objects.filter(
                dossier__patient=patient  # navigation ForeignKey inversée
            ).count(),
        }

        # Les 5 dernières consultations pour l'historique du dashboard
        ctx['consultations_recentes'] = Consultation.objects.filter(
            dossier__patient=patient
        ).select_related('medecin__user').order_by('-date_consultation')[:5]

        return ctx


class ListePatientsView(LoginRequiredMixin, ListView):
    """
    Liste paginée de tous les patients avec recherche multicritères.

    annotate(nb_rdv=Count('rendez_vous')) : ajoute une colonne calculée SQL
    → le nombre de RDV par patient, disponible dans le template comme {{ patient.nb_rdv }}.
    → Évite le problème N+1 (une seule requête SQL avec JOIN + GROUP BY).

    Filtres combinables :
      q      : recherche textuelle sur prénom, nom, email (Q() avec OR)
      sexe   : filtre exact (M/F)
      statut : filtre sur le statut du compte User (actif, inactif, suspendu)

    Q() avec | : génère un WHERE (condition1 OR condition2 OR condition3) en SQL.
    Sans Q(), chaque .filter() chaîné génère des AND.
    """

    model = Patient
    template_name = 'patients/liste_patients.html'
    context_object_name = 'patients'
    paginate_by = 15  # 15 patients par page

    def get_queryset(self):
        # select_related : JOIN SQL sur la table User (évite N+1 pour patient.user.nom)
        # annotate : COUNT SQL du nombre de rendez-vous par patient
        qs = Patient.objects.select_related('user').annotate(
            nb_rdv=Count('rendez_vous')
        )

        # Récupération des paramètres GET (vides par défaut si absents)
        q      = self.request.GET.get('q', '')
        sexe   = self.request.GET.get('sexe', '')
        statut = self.request.GET.get('statut', '')

        if q:
            # Q() avec | génère un WHERE ... OR ... OR ... en SQL
            # icontains : insensible à la casse (ILIKE '%q%' en PostgreSQL)
            qs = qs.filter(
                Q(user__first_name__icontains=q) |
                Q(user__last_name__icontains=q)  |
                Q(user__email__icontains=q)
            )
        if sexe:
            qs = qs.filter(sexe=sexe)     # filtre exact sur le champ sexe
        if statut:
            qs = qs.filter(user__statut=statut)  # filtre sur le statut du User lié

        return qs.order_by('user__last_name')  # tri alphabétique par nom

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Re-injection des filtres pour que le formulaire garde les valeurs sélectionnées
        ctx['q']               = self.request.GET.get('q', '')
        ctx['selected_sexe']   = self.request.GET.get('sexe', '')
        ctx['selected_statut'] = self.request.GET.get('statut', '')
        return ctx


class DetailPatientView(LoginRequiredMixin, DetailView):
    """
    Fiche complète d'un patient.

    DetailView gère automatiquement : récupération par pk (depuis l'URL),
    404 si inexistant, passage de l'objet dans le contexte sous 'patient'.
    """

    model = Patient
    template_name = 'patients/detail_patient.html'
    context_object_name = 'patient'


class CreerPatientView(AdminRequiredMixin, View):
    """
    Création d'un nouveau compte patient (admin seulement).

    Deux formulaires liés :
      CreerPatientUserForm  → crée le User (email, mot de passe, rôle=PATIENT)
      PatientProfileForm    → crée le Patient (date naissance, sexe, groupe sanguin…)

    @transaction.atomic sur post() : si la création du profil Patient échoue après
    la création du User, la transaction est annulée → pas de User sans Patient associé.
    C'est l'atomicité des transactions SQL : tout ou rien.

    commit=False sur profile_form.save() : crée l'objet Patient en mémoire sans
    l'insérer en base → permet de remplir patient.user avant le vrai INSERT.
    """

    template_name = 'patients/creer_patient.html'

    def get(self, request):
        # Formulaires vides pour l'affichage initial
        return render(request, self.template_name, {
            'user_form':    CreerPatientUserForm(),
            'profile_form': PatientProfileForm(),
        })

    @transaction.atomic  # si une étape échoue, tout est annulé (rollback SQL)
    def post(self, request):
        user_form    = CreerPatientUserForm(request.POST)
        profile_form = PatientProfileForm(request.POST)

        if user_form.is_valid() and profile_form.is_valid():
            user           = user_form.save()           # INSERT dans auth_user
            patient        = profile_form.save(commit=False)  # objet en mémoire seulement
            patient.user   = user                       # liaison User → Patient
            patient.save()                              # INSERT dans patients_patient
            messages.success(request, f'Patient {user.get_full_name()} créé avec succès.')
            return redirect('patients:detail', pk=patient.pk)

        # Re-affichage du formulaire avec les erreurs de validation
        return render(request, self.template_name, {
            'user_form':    user_form,
            'profile_form': profile_form,
        })


class ModifierPatientView(AdminRequiredMixin, View):
    """
    Modification du compte et du profil d'un patient (admin seulement).

    _get_patient() : méthode helper privée (préfixe _) partagée entre get() et post()
    pour éviter la duplication. select_related('user') → JOIN SQL pour éviter N+1.

    @transaction.atomic sur post() : les deux saves() (user_form + profile_form)
    sont dans la même transaction → si l'un échoue, l'autre est annulé.

    instance=patient.user / instance=patient → UPDATE SQL sur les enregistrements
    existants (pas de création de nouveaux objets).
    """

    template_name = 'patients/modifier_patient.html'

    def _get_patient(self, pk):
        """Helper : récupère le patient avec son User en un seul JOIN (select_related)."""
        return get_object_or_404(Patient.objects.select_related('user'), pk=pk)

    def get(self, request, pk):
        patient = self._get_patient(pk)
        # instance= pré-remplit les formulaires avec les données actuelles
        return render(request, self.template_name, {
            'patient':      patient,
            'user_form':    ModifierPatientUserForm(instance=patient.user),
            'profile_form': PatientProfileForm(instance=patient),
        })

    @transaction.atomic  # atomicité : les deux UPDATE réussissent ou aucun
    def post(self, request, pk):
        patient      = self._get_patient(pk)
        user_form    = ModifierPatientUserForm(request.POST, instance=patient.user)
        profile_form = PatientProfileForm(request.POST, instance=patient)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()     # UPDATE SQL sur la table User
            profile_form.save()  # UPDATE SQL sur la table Patient
            messages.success(request, 'Patient modifié avec succès.')
            return redirect('patients:detail', pk=patient.pk)

        return render(request, self.template_name, {
            'patient':      patient,
            'user_form':    user_form,
            'profile_form': profile_form,
        })


class SupprimerPatientView(AdminRequiredMixin, View):
    """
    Supprime un patient et son compte utilisateur.

    patient.user.delete() : on supprime le User, pas le Patient directement.
    Pourquoi ? Le Patient a un OneToOneField vers User avec on_delete=CASCADE.
    Supprimer le User déclenche la cascade et supprime le Patient automatiquement.
    Cela supprime aussi tous les RendezVous liés (si on_delete=CASCADE côté RDV).

    nom = patient.nom_complet : récupéré avant la suppression pour le message flash.
    Après delete(), l'objet n'est plus en base et ses attributs sont inaccessibles.
    """

    def post(self, request, pk):
        patient = get_object_or_404(Patient.objects.select_related('user'), pk=pk)
        nom     = patient.nom_complet     # sauvegardé avant la suppression
        patient.user.delete()             # CASCADE → supprime User + Patient + données liées
        messages.success(request, f'Patient {nom} supprimé.')
        return redirect('patients:liste')
