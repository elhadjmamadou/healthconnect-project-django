# ==============================================================================
# paiements/views.py — Vues du module paiement
# ==============================================================================
# Ce fichier contient les vues liées aux paiements de consultations.
# La vue principale (PayerRDVView) simule un paiement mobile money sans
# aucun appel API réel — c'est un environnement de démonstration "vitrine".
#
# Flux complet :
#   Patient → Page détail RDV → clic "Payer" → PayerRDVView (GET)
#   → Patient choisit opérateur et saisit numéro → PayerRDVView (POST)
#   → Animation JS 4.6 secondes → Formulaire soumis → Paiement confirmé en BDD
#   → Redirection vers PaiementSuccesView
# ==============================================================================

import json
import uuid

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView

from users.mixins import PatientRequiredMixin

from .models import Paiement


class ListePaiementsView(LoginRequiredMixin, ListView):
    """
    Liste des paiements avec filtrage par rôle.

    - Patient : voit seulement ses propres paiements
    - Médecin : voit les paiements de ses consultations
    - Admin/Staff : voit tous les paiements
    """

    model = Paiement
    template_name = 'paiements/liste_paiements.html'
    context_object_name = 'paiements'
    paginate_by = 20

    def get_queryset(self):
        """
        Construit le queryset selon le rôle de l'utilisateur.

        select_related() : évite les requêtes N+1 en faisant des JOIN SQL
        sur les relations ForeignKey/OneToOneField. Ici on précharge le
        chemin complet patient.user et medecin.user pour afficher les noms.

        models.Q() : permet de combiner des conditions avec OR (|).
        Sans Q(), filter() ne sait faire que du AND.
        """
        qs = Paiement.objects.select_related(
            'rendez_vous__patient__user',
            'rendez_vous__medecin__user',
            'consultation__dossier__patient__user',
            'consultation__medecin__user',
        )
        user = self.request.user

        # Restriction de visibilité selon le rôle
        if user.is_patient:
            # Le patient voit ses paiements liés à ses RDV ou ses consultations
            qs = qs.filter(
                models.Q(rendez_vous__patient__user=user)
                | models.Q(consultation__dossier__patient__user=user)
            )
        elif user.is_medecin:
            # Le médecin voit les paiements liés à ses RDV ou ses consultations
            qs = qs.filter(
                models.Q(rendez_vous__medecin__user=user)
                | models.Q(consultation__medecin__user=user)
            )
        # Admin/staff : pas de filtre → voit tout

        # Filtres GET (URL : ?statut=confirme&mode=orange_money)
        statut = self.request.GET.get('statut', '')
        mode   = self.request.GET.get('mode', '')
        if statut:
            qs = qs.filter(statut_paiement=statut)
        if mode:
            qs = qs.filter(mode_paiement=mode)

        return qs.order_by('-date_creation')

    def get_context_data(self, **kwargs):
        """Ajoute les KPI du mois courant au contexte du template."""
        ctx = super().get_context_data(**kwargs)
        today      = timezone.localdate()
        month_start = today.replace(day=1)
        qs_month   = Paiement.objects.filter(date_creation__date__gte=month_start)

        ctx['kpi'] = {
            # aggregate(t=Sum('montant')) retourne {'t': valeur} ou {'t': None}
            # Le "or 0" gère le cas sans données
            'total_encaisse': qs_month.filter(statut_paiement='confirme').aggregate(t=Sum('montant'))['t'] or 0,
            'en_attente': qs_month.filter(statut_paiement__in=['en_attente', 'initie']).count(),
            'echoues':    qs_month.filter(statut_paiement='echoue').count(),
        }
        ctx['selected_statut'] = self.request.GET.get('statut', '')
        ctx['selected_mode']   = self.request.GET.get('mode', '')
        return ctx


class DetailPaiementView(LoginRequiredMixin, DetailView):
    """Détail d'un paiement — reçu de transaction."""

    model = Paiement
    template_name = 'paiements/detail_paiement.html'
    context_object_name = 'paiement'

    def get_queryset(self):
        """Précharge toutes les relations pour éviter les requêtes supplémentaires."""
        return Paiement.objects.select_related(
            'rendez_vous__patient__user',
            'rendez_vous__medecin__user',
            'consultation__dossier__patient__user',
            'consultation__medecin__user',
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        paiement     = self.object
        consultation = paiement.consultation
        if consultation:
            # Historique des paiements liés à la même consultation (remboursements…)
            ctx['historique_paiements'] = Paiement.objects.filter(
                consultation=consultation
            ).exclude(pk=paiement.pk).order_by('-date_creation')
        else:
            ctx['historique_paiements'] = Paiement.objects.none()
        return ctx


# ------------------------------------------------------------------
# Données des opérateurs mobile money guinéens
# Utilisées dans le formulaire de choix d'opérateur (payer_rdv.html).
# La couleur hexadécimale est affichée dans la carte radio de chaque opérateur.
# ------------------------------------------------------------------
MODES_MOBILE = [
    {'code': 'orange_money', 'nom': 'Orange Money', 'couleur': '#ff7900'},  # orange
    {'code': 'mtn_money',    'nom': 'MTN Money',    'couleur': '#ffcc00'},  # jaune
    {'code': 'wave',         'nom': 'Wave',         'couleur': '#1dc8ff'},  # bleu
]


class PayerRDVView(PatientRequiredMixin, View):
    """
    Page de paiement d'une consultation — simulation vitrine sans appel API réel.

    PatientRequiredMixin garantit :
      1. L'utilisateur est connecté (sinon → page login)
      2. L'utilisateur a le rôle PATIENT (sinon → 403 Forbidden)

    GET  → affiche le formulaire de choix d'opérateur et de numéro de téléphone
    POST → simule le paiement et confirme directement le Paiement en base de données
    """

    template_name = 'paiements/payer_rdv.html'

    def _get_rdv(self, request, pk):
        """
        Récupère le RDV ou lève une 404.
        Lève PermissionDenied si le RDV n'appartient pas à l'utilisateur connecté.
        """
        from rendez_vous.models import RendezVous
        rdv = get_object_or_404(
            RendezVous.objects.select_related('medecin__user', 'patient__user'),
            pk=pk,
        )
        # Vérification que le patient connecté est bien celui du RDV
        if rdv.patient.user != request.user:
            raise PermissionDenied
        return rdv

    def _controler(self, request, rdv):
        """
        Vérifie les préconditions métier avant d'afficher ou de traiter le paiement.

        Retourne une redirection si le paiement est impossible, None sinon.
        Centralisé ici pour éviter la duplication entre GET et POST.
        """
        paiement = getattr(rdv, 'paiement', None)

        # Cas 1 : déjà payé → rediriger vers le reçu
        if paiement and paiement.est_paye:
            messages.info(request, 'Cette consultation est déjà payée.')
            return redirect('paiements:detail', pk=paiement.pk)

        # Cas 2 : RDV annulé ou terminé → paiement impossible
        if not rdv.est_actif:
            messages.error(request, 'Ce rendez-vous ne peut plus être payé.')
            return redirect('rendez_vous:detail', pk=rdv.pk)

        # Cas 3 : tarif non défini (0) → paiement non applicable
        if rdv.medecin.tarif_consultation <= 0:
            messages.error(request, "Le tarif de ce médecin n'est pas encore défini.")
            return redirect('rendez_vous:detail', pk=rdv.pk)

        return None  # tout est OK, on peut continuer

    def get(self, request, pk):
        """Affiche la page de paiement avec le récapitulatif et le formulaire."""
        rdv = self._get_rdv(request, pk)
        redirection = self._controler(request, rdv)
        if redirection:
            return redirection
        return render(request, self.template_name, {
            'rdv':              rdv,
            'tarif':            rdv.medecin.tarif_consultation,
            'modes':            MODES_MOBILE,
            # Pré-remplissage du numéro de téléphone depuis le profil utilisateur
            'telephone_defaut': request.user.telephone,
        })

    def post(self, request, pk):
        """
        Traite le formulaire de paiement et simule la confirmation.

        En production, cette méthode :
          1. Créerait un Paiement avec statut EN_ATTENTE
          2. Appellerait DjomyClient().initier_paiement(...)
          3. Attendrait le webhook Djomy pour confirmer (WebhookDjomyView)

        En démonstration :
          1. On crée directement un Paiement avec statut CONFIRME
          2. On génère une fausse référence Djomy (DJM-SIM-...)
          3. On stocke un payload simulé dans webhook_payload
          → Le signal creer_notification_paiement est déclenché automatiquement
            car le statut devient CONFIRME (notifications/signals.py)
        """
        rdv = self._get_rdv(request, pk)
        redirection = self._controler(request, rdv)
        if redirection:
            return redirection

        mode      = request.POST.get('mode_paiement', '')
        telephone = request.POST.get('telephone', '').strip()

        # Validation basique : opérateur connu + numéro renseigné
        if mode not in {m['code'] for m in MODES_MOBILE} or not telephone:
            messages.error(request, 'Choisissez un opérateur et renseignez votre numéro.')
            return redirect('paiements:payer_rdv', pk=rdv.pk)

        # Génération d'une fausse référence Djomy pour la démo
        reference_djomy = 'DJM-SIM-' + uuid.uuid4().hex[:10].upper()

        # update_or_create : crée le Paiement s'il n'existe pas, le met à jour sinon
        # (évite les doublons si l'utilisateur soumet deux fois le formulaire)
        paiement, _ = Paiement.objects.update_or_create(
            rendez_vous=rdv,
            defaults={
                'montant':          rdv.medecin.tarif_consultation,
                'devise':           'GNF',
                'mode_paiement':    mode,
                'statut_paiement':  Paiement.StatutPaiement.CONFIRME,  # confirmation immédiate
                'date_paiement':    timezone.now(),
                'reference_djomy':  reference_djomy,
                # Payload qui imite la structure d'une vraie réponse Djomy
                'webhook_payload': {
                    'simulation':     True,
                    'status':         'success',
                    'transaction_id': reference_djomy,
                    'phone':          telephone,
                    'amount':         float(rdv.medecin.tarif_consultation),
                    'currency':       'GNF',
                    'operator':       mode,
                    'processed_at':   timezone.now().isoformat(),
                },
            },
        )

        # La sauvegarde du Paiement déclenche le signal post_save
        # → creer_notification_paiement dans notifications/signals.py
        # → une notification est créée et un e-mail envoyé au patient
        return redirect('paiements:succes', pk=paiement.pk)


class PaiementSuccesView(LoginRequiredMixin, DetailView):
    """
    Page de confirmation de paiement (reçu animé).

    Le queryset filtre sur rendez_vous__patient__user=request.user pour
    qu'un patient ne puisse pas accéder au reçu d'un autre patient
    en devinant l'ID du paiement dans l'URL.
    """

    model = Paiement
    template_name = 'paiements/paiement_succes.html'
    context_object_name = 'paiement'

    def get_queryset(self):
        return Paiement.objects.select_related(
            'rendez_vous__patient__user', 'rendez_vous__medecin__user'
        ).filter(rendez_vous__patient__user=self.request.user)


class WebhookDjomyView(View):
    """
    Endpoint de réception des webhooks Djomy.

    URL : /paiements/webhook/djomy/ (pas de LoginRequired — appelé par Djomy)

    Sécurité : chaque requête est validée par signature HMAC-SHA256.
    Si la signature est invalide → 400 Bad Request.
    Si la signature est valide  → mise à jour du statut du paiement en base.

    Djomy envoie un webhook dès qu'une transaction change de statut
    (pending → success ou failed). Le champ 'reference' dans le payload
    correspond à notre reference_interne (PAY-XXXXXXXXXX).
    """

    def post(self, request):
        from .djomy_client import DjomyClient

        # L'en-tête X-Djomy-Signature contient le HMAC calculé par Djomy
        signature = request.headers.get('X-Djomy-Signature', '')
        try:
            client = DjomyClient()
            # traiter_webhook() vérifie la signature et décode le JSON
            data = client.traiter_webhook(request.body, signature)

            reference = data.get('reference', '')  # notre référence interne
            statut    = data.get('status', '')      # 'success', 'failed', 'pending'

            if reference:
                # Correspondance entre les statuts Djomy et nos statuts internes
                mapping = {
                    'success': 'confirme',
                    'failed':  'echoue',
                    'pending': 'initie',
                }
                # update() : mise à jour directe en base sans charger l'objet
                Paiement.objects.filter(reference_interne=reference).update(
                    statut_paiement=mapping.get(statut, 'en_attente'),
                    reference_djomy=data.get('transaction_id', ''),
                    webhook_payload=data,
                )

            # Djomy attend une réponse 200 pour considérer le webhook comme reçu
            return JsonResponse({'status': 'ok'})

        except ValueError:
            # Signature invalide → requête rejetée
            return JsonResponse({'error': 'Signature invalide'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
