# ==============================================================================
# consultations/views.py — Vues des dossiers, consultations et ordonnances
# ==============================================================================
# Ce fichier gère l'ensemble du parcours médical numérique :
#
#   MonDossierView          : redirige le patient vers son dossier médical
#   DossierMedicalView      : affiche un dossier et son historique
#   ListeDossiersView       : liste admin de tous les dossiers
#   ListeConsultationsView  : liste de toutes les consultations
#   CreerConsultationView   : médecin crée un compte-rendu en fin de RDV
#   EditerConsultationView  : médecin modifie son compte-rendu
#   DetailConsultationView  : lecture détaillée d'une consultation
#   RedigerOrdonnanceView   : médecin crée/modifie l'ordonnance numérique
#   OrdonnancePDFView       : génère le PDF de l'ordonnance via WeasyPrint
#   VerifierOrdonnanceView  : page publique de vérification QR code
#   SupprimerConsultationView : suppression (médecin ou admin)
# ==============================================================================

import base64
import io

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils import timezone
from django.db import models
from django.db.models import Count
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView, View

from users.mixins import AdminRequiredMixin, MedecinRequiredMixin
from rendez_vous.models import RendezVous

from .forms import ConsultationForm
from .models import Consultation, DossierMedical, LigneOrdonnance, Ordonnance


class MonDossierView(LoginRequiredMixin, View):
    """
    Raccourci pour accéder à son propre dossier médical.

    URL : /consultations/mon-dossier/
    Le patient n'a pas à connaître l'ID de son dossier — cette vue
    le récupère depuis son profil et redirige vers DossierMedicalView.
    """

    def get(self, request):
        try:
            dossier = request.user.patient_profile.dossier_medical
        except Exception:
            # Cas anormal : patient sans dossier médical → 404 plutôt qu'erreur 500
            raise Http404("Dossier médical introuvable.")
        return redirect('consultations:dossier', pk=dossier.pk)


class DossierMedicalView(LoginRequiredMixin, DetailView):
    """
    Affiche un dossier médical et l'historique de ses consultations.

    Accès : patient concerné, médecin ayant consulté, admin.
    (Note : le contrôle d'accès fin est délégué à la vue ou au template.)
    """

    model = DossierMedical
    template_name = 'consultations/dossier_medical.html'
    context_object_name = 'dossier'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Précharge le médecin de chaque consultation pour éviter les requêtes N+1
        ctx['consultations'] = self.object.consultations.select_related(
            'medecin__user'
        ).order_by('-date_consultation')
        return ctx


class ListeDossiersView(LoginRequiredMixin, ListView):
    """
    Liste de tous les dossiers médicaux — réservée aux admins.

    dispatch() est appelé AVANT get() ou post() : c'est le point
    d'entrée de toute requête. On l'utilise ici pour vérifier les droits
    avant même que la vue soit instanciée.
    """

    model = DossierMedical
    template_name = 'consultations/liste_dossiers.html'
    context_object_name = 'dossiers'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        """Vérifie que l'utilisateur est admin ou staff avant de continuer."""
        if not (request.user.is_staff or request.user.is_admin_role):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """Filtre par nom ou numéro de dossier si un paramètre q est passé."""
        qs = DossierMedical.objects.select_related(
            'patient__user'
        ).annotate(nb_consultations=Count('consultations')).order_by('-date_creation')

        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                models.Q(patient__user__first_name__icontains=q) |
                models.Q(patient__user__last_name__icontains=q) |
                models.Q(numero_dossier__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class ListeConsultationsView(LoginRequiredMixin, ListView):
    """Liste toutes les consultations (usage admin / debug)."""

    model = Consultation
    template_name = 'consultations/liste_consultations.html'
    context_object_name = 'consultations'
    paginate_by = 20

    def get_queryset(self):
        return Consultation.objects.select_related(
            'dossier__patient__user', 'medecin__user'
        ).order_by('-date_consultation')


class CreerConsultationView(MedecinRequiredMixin, SuccessMessageMixin, CreateView):
    """
    Crée une consultation liée à un rendez-vous.

    Flux :
      1. Le médecin clique "Créer la consultation" depuis la fiche du RDV
      2. Il remplit le formulaire (compte-rendu, diagnostic, prescription)
      3. La consultation est créée + le RDV est marqué TERMINE

    SuccessMessageMixin : ajoute automatiquement le message de succès
    après une création réussie (sans avoir à appeler messages.success()).

    @transaction.atomic sur form_valid() : si la mise à jour du statut RDV
    échoue, la création de la consultation est annulée (cohérence BDD).
    """

    model = Consultation
    form_class = ConsultationForm
    template_name = 'consultations/creer_consultation.html'
    success_message = 'Consultation créée avec succès.'

    def dispatch(self, request, *args, **kwargs):
        """Vérifie que le RDV existe et appartient bien au médecin connecté."""
        self.rdv = get_object_or_404(RendezVous, pk=kwargs['rdv_pk'])
        if self.rdv.medecin != request.user.medecin_profile:
            raise Http404("Vous n'avez pas accès à ce rendez-vous.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['rdv']     = self.rdv
        ctx['patient'] = self.rdv.patient
        ctx['dossier'] = self.rdv.patient.dossier_medical
        return ctx

    @transaction.atomic
    def form_valid(self, form):
        """
        Sauvegarde la consultation et marque le RDV comme terminé.

        commit=False : on construit l'objet sans le sauvegarder immédiatement,
        ce qui nous permet d'attacher les champs manquants (dossier, medecin, etc.)
        avant le premier INSERT en base de données.
        """
        consultation = form.save(commit=False)
        consultation.dossier    = self.rdv.patient.dossier_medical
        consultation.medecin    = self.request.user.medecin_profile
        consultation.rendez_vous = self.rdv
        consultation.date_consultation = timezone.now()
        consultation.save()

        # Passage du RDV à TERMINE → déclenche le signal dans notifications/signals.py
        self.rdv.statut_rdv = RendezVous.StatutRdv.TERMINE
        self.rdv.save()

        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy('consultations:detail', kwargs={'pk': self.object.pk})


class EditerConsultationView(MedecinRequiredMixin, SuccessMessageMixin, UpdateView):
    """
    Modifie une consultation existante (médecin auteur seulement).

    get_queryset() filtre sur medecin=request.user.medecin_profile :
    un médecin ne peut modifier que SES consultations, jamais celles d'un confrère.
    """

    model = Consultation
    form_class = ConsultationForm
    template_name = 'consultations/editer_consultation.html'
    success_message = 'Consultation mise à jour avec succès.'

    def get_queryset(self):
        return Consultation.objects.filter(medecin=self.request.user.medecin_profile)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['patient'] = self.object.dossier.patient
        ctx['dossier'] = self.object.dossier
        return ctx

    def get_success_url(self):
        return reverse_lazy('consultations:detail', kwargs={'pk': self.object.pk})


class DetailConsultationView(LoginRequiredMixin, DetailView):
    """
    Affiche les détails d'une consultation.

    Contrôle d'accès granulaire dans get_queryset() :
      - Admin/staff : toutes les consultations
      - Médecin : uniquement ses consultations
      - Patient : uniquement les consultations de son dossier

    Si l'ID passé en URL ne correspond pas au filtre, get_object() lève
    automatiquement une 404 (comportement Django par défaut avec DetailView).
    """

    model = Consultation
    template_name = 'consultations/detail_consultation.html'
    context_object_name = 'consultation'

    def get_queryset(self):
        qs = Consultation.objects.select_related(
            'dossier__patient__user', 'medecin__user', 'rendez_vous'
        )
        user = self.request.user

        if user.is_admin_role or user.is_staff:
            return qs                                          # accès complet

        if user.is_medecin:
            return qs.filter(medecin=user.medecin_profile)    # ses consultations uniquement

        if user.is_patient:
            return qs.filter(dossier__patient__user=user)     # son dossier uniquement

        return qs.none()  # aucune permission → queryset vide → 404

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['patient']  = self.object.dossier.patient
        ctx['dossier']  = self.object.dossier
        # Droit d'édition : uniquement le médecin qui a créé la consultation
        ctx['can_edit'] = (
            self.request.user.is_medecin and
            self.object.medecin == self.request.user.medecin_profile
        )
        return ctx


class RedigerOrdonnanceView(MedecinRequiredMixin, View):
    """
    Création ou modification de l'ordonnance d'une consultation.

    Une consultation ne peut avoir qu'UNE ordonnance (OneToOneField).
    Si une ordonnance existe déjà, on la met à jour (update_or_create).

    Le formulaire est dynamique : le médecin peut ajouter/supprimer des
    lignes de médicaments via JavaScript (template rediger_ordonnance.html).
    Les données arrivent sous forme de listes parallèles :
      medicament[] = ["Paracétamol", "Amoxicilline"]
      posologie[]  = ["3x/jour", "2x/jour"]
      duree[]      = ["5 jours", "7 jours"]
    """

    template_name = 'consultations/rediger_ordonnance.html'

    def _get_consultation(self, request, pk):
        """
        Récupère la consultation ET vérifie que c'est bien celle du médecin connecté.
        Lève une 404 si la consultation n'existe pas ou n'appartient pas au médecin.
        """
        return get_object_or_404(
            Consultation.objects.select_related('dossier__patient__user', 'medecin__user'),
            pk=pk,
            medecin=request.user.medecin_profile,  # filtre de sécurité
        )

    def get(self, request, pk):
        """Affiche le formulaire, pré-rempli si une ordonnance existe déjà."""
        consultation = self._get_consultation(request, pk)
        ordonnance = getattr(consultation, 'ordonnance', None)  # None si pas d'ordonnance
        return render(request, self.template_name, {
            'consultation': consultation,
            'patient':      consultation.dossier.patient,
            'ordonnance':   ordonnance,
            'lignes':       ordonnance.lignes.all() if ordonnance else [],
        })

    @transaction.atomic
    def post(self, request, pk):
        """
        Traite la soumission du formulaire d'ordonnance.

        Étapes :
          1. Récupérer les listes de médicaments/posologies/durées depuis POST
          2. Zipper les 3 listes en tuples (médicament, posologie, durée)
          3. Filtrer les lignes vides (médicament blanc = supprimé par le médecin)
          4. Créer ou mettre à jour l'ordonnance (update_or_create)
          5. Supprimer les anciennes lignes et créer les nouvelles (bulk_create)

        bulk_create() : INSERT multiple en UNE seule requête SQL (plus rapide
        et atomique que N appels à LigneOrdonnance.objects.create()).
        """
        consultation = self._get_consultation(request, pk)

        # Récupération des listes de valeurs depuis le formulaire HTML
        medicaments = request.POST.getlist('medicament')
        posologies  = request.POST.getlist('posologie')
        durees      = request.POST.getlist('duree')

        # zip() aligne les 3 listes en tuples, strip() supprime les espaces superflus
        lignes = [
            (med.strip(), pos.strip(), dur.strip())
            for med, pos, dur in zip(medicaments, posologies, durees)
            if med.strip()  # on ignore les lignes où le médicament est vide
        ]

        if not lignes:
            messages.error(request, 'Ajoutez au moins un médicament à l\'ordonnance.')
            return redirect('consultations:rediger_ordonnance', pk=consultation.pk)

        # update_or_create : crée l'ordonnance si elle n'existe pas, la met à jour sinon
        # (la clé de recherche est `consultation=consultation`)
        ordonnance, _ = Ordonnance.objects.update_or_create(
            consultation=consultation,
            defaults={'instructions': request.POST.get('instructions', '').strip()},
        )

        # Remplacement complet des lignes : suppression + recréation
        # Plus simple et fiable que de calculer les diffs à mettre à jour
        ordonnance.lignes.all().delete()
        LigneOrdonnance.objects.bulk_create([
            LigneOrdonnance(
                ordonnance=ordonnance,
                medicament=med,
                posologie=pos,
                duree=dur,
                ordre=i,          # préserve l'ordre de saisie du médecin
            )
            for i, (med, pos, dur) in enumerate(lignes)
        ])

        messages.success(request, f'Ordonnance {ordonnance.numero} enregistrée.')
        return redirect('consultations:detail', pk=consultation.pk)


def _qr_data_uri(contenu):
    """
    Génère un QR code en mémoire et retourne une data URI PNG base64.

    Pourquoi une data URI et pas une URL externe ?
    WeasyPrint (le moteur PDF) ne peut pas charger de ressources réseau
    en production (sécurité). Une data URI embarque directement l'image
    dans le HTML → le PDF est autoportant.

    Processus :
      1. qrcode.make() génère l'image QR en objet PIL
      2. io.BytesIO() crée un buffer mémoire (pas de fichier disque)
      3. img.save(buffer) écrit le PNG dans le buffer
      4. base64.b64encode() encode les bytes en chaîne ASCII
      5. On préfixe avec 'data:image/png;base64,' pour que le navigateur
         ou WeasyPrint comprenne que c'est une image PNG embarquée

    Args:
        contenu (str): Texte à encoder dans le QR code (URL de vérification).

    Returns:
        str: Data URI de type 'data:image/png;base64,<données>'.
    """
    import qrcode
    img    = qrcode.make(contenu, box_size=6, border=2)
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode()


class OrdonnancePDFView(LoginRequiredMixin, View):
    """
    Génère et retourne le PDF de l'ordonnance.

    Le PDF est généré à la volée par WeasyPrint qui convertit le HTML du
    template consultations/pdf/ordonnance.html en PDF. Le QR code est
    embarqué comme data URI (voir _qr_data_uri ci-dessus).

    Content-Disposition: inline → le PDF s'ouvre dans le navigateur.
    Changer en 'attachment' pour forcer le téléchargement.

    Accès :
      - Admin/staff : toutes les ordonnances
      - Médecin : uniquement ses ordonnances
      - Patient : uniquement ses ordonnances
    """

    def get(self, request, pk):
        from weasyprint import HTML

        # Construction du queryset avec préchargement de toutes les relations nécessaires
        qs = Ordonnance.objects.select_related(
            'consultation__dossier__patient__user',
            'consultation__medecin__user',
        ).prefetch_related('lignes', 'consultation__medecin__specialites')

        # Contrôle d'accès selon le rôle
        user = request.user
        if user.is_admin_role or user.is_staff:
            pass                                          # accès complet
        elif user.is_medecin:
            qs = qs.filter(consultation__medecin__user=user)
        elif user.is_patient:
            qs = qs.filter(consultation__dossier__patient__user=user)
        else:
            qs = qs.none()

        ordonnance = get_object_or_404(qs, pk=pk)

        # Génération de l'URL publique de vérification (encodée dans le QR)
        url_verification = request.build_absolute_uri(
            reverse_lazy(
                'consultations:verifier_ordonnance',
                kwargs={'token': ordonnance.token_verification}
            )
        )

        # Rendu du template HTML en chaîne de caractères pour WeasyPrint
        html = render_to_string('consultations/pdf/ordonnance.html', {
            'ordonnance':    ordonnance,
            'consultation':  ordonnance.consultation,
            'medecin':       ordonnance.medecin,
            'patient':       ordonnance.patient,
            'lignes':        ordonnance.lignes.all(),
            'qr_data_uri':   _qr_data_uri(url_verification),  # QR code en base64
            'url_verification': url_verification,
        })

        # Conversion HTML → PDF par WeasyPrint
        pdf = HTML(string=html).write_pdf()

        response = HttpResponse(pdf, content_type='application/pdf')
        # inline : ouverture dans le navigateur (pas téléchargement forcé)
        response['Content-Disposition'] = f'inline; filename="{ordonnance.numero}.pdf"'
        return response


class VerifierOrdonnanceView(View):
    """
    Page publique de vérification d'authenticité d'une ordonnance.

    Cette page est accessible à TOUS, sans connexion (un pharmacien doit
    pouvoir la scanner depuis son téléphone sans avoir de compte).

    Le token UUID est encodé dans le QR code de l'ordonnance PDF.
    Il est impossible de deviner → seul quelqu'un qui a l'ordonnance physique
    peut accéder à la page de vérification.

    Si le token existe en base → ordonnance authentique.
    Si le token n'existe pas  → ordonnance falsifiée ou invalide.
    """

    template_name = 'consultations/verifier_ordonnance.html'

    def get(self, request, token):
        # On cherche l'ordonnance par son token UUID unique
        # .first() retourne None si aucun résultat (pas d'exception)
        ordonnance = Ordonnance.objects.select_related(
            'consultation__dossier__patient__user',
            'consultation__medecin__user',
        ).filter(token_verification=token).first()

        return render(request, self.template_name, {
            'ordonnance': ordonnance,
            'valide':     ordonnance is not None,  # True si trouvée, False sinon
        })


class SupprimerConsultationView(LoginRequiredMixin, View):
    """
    Supprime une consultation.

    Admins/staff : peuvent supprimer n'importe quelle consultation.
    Médecin      : peut supprimer uniquement ses consultations.
    Patient      : ne peut pas supprimer.
    """

    def post(self, request, pk):
        qs = Consultation.objects.select_related('medecin__user', 'dossier')

        if request.user.is_staff or request.user.is_admin_role:
            consultation = get_object_or_404(qs, pk=pk)
        elif request.user.is_medecin:
            consultation = get_object_or_404(qs, pk=pk, medecin=request.user.medecin_profile)
        else:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied

        dossier_pk = consultation.dossier.pk
        consultation.delete()
        messages.success(request, 'Consultation supprimée.')
        # Retour au dossier médical du patient
        return redirect('consultations:dossier', pk=dossier_pk)
