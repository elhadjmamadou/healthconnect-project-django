# ==============================================================================
# disponibilites/views.py — Gestion des créneaux de disponibilité des médecins
# ==============================================================================
# Un médecin publie ses créneaux à l'avance pour que les patients puissent
# réserver en ligne. Ce fichier contient 4 vues (formulaire + 3 actions) :
#
# DisponibiliteForm       : formulaire de création/modification d'un créneau
# ListeDisponibilitesView : tableau de bord des créneaux du médecin connecté
# AjouterDisponibiliteView : POST → crée un nouveau créneau
# ModifierDisponibiliteView : POST → modifie un créneau existant (si libre)
# SupprimerDisponibiliteView : POST → supprime un créneau (si libre)
#
# Seuls les médecins peuvent accéder à ces vues (MedecinRequiredMixin).
# Un médecin ne peut modifier/supprimer QUE ses propres créneaux
# (filtre medecin__user=request.user dans les querysets).
# ==============================================================================

from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView

from users.mixins import MedecinRequiredMixin
from .models import Disponibilite


class DisponibiliteForm(forms.ModelForm):
    """
    Formulaire de création / modification d'un créneau de disponibilité.

    Widgets HTML5 :
      type="date" → sélecteur de date natif du navigateur (sans JS supplémentaire)
      type="time" → sélecteur d'heure natif du navigateur

    La validation anti-chevauchement est effectuée dans Disponibilite.clean()
    (disponibilites/models.py), appelée automatiquement par form.save().
    Si un chevauchement est détecté, form.save() lève une ValidationError
    qui est capturée dans AjouterDisponibiliteView pour afficher un message d'erreur.
    """

    class Meta:
        model  = Disponibilite
        fields = ['date_disponibilite', 'heure_debut', 'heure_fin', 'type_creneau']
        widgets = {
            'date_disponibilite': forms.DateInput(attrs={'type': 'date'}),
            'heure_debut':        forms.TimeInput(attrs={'type': 'time'}),
            'heure_fin':          forms.TimeInput(attrs={'type': 'time'}),
            'type_creneau':       forms.Select(),
        }


class ListeDisponibilitesView(MedecinRequiredMixin, ListView):
    """
    Liste des créneaux du médecin connecté avec statistiques rapides.

    MedecinRequiredMixin : seuls les médecins accèdent à cette page.
    Le queryset filtre sur medecin__user=request.user → un médecin ne voit
    que SES propres créneaux, jamais ceux d'un confrère.

    get_context_data() calcule 3 compteurs (libres, réservés, total)
    affichés en KPI en haut de la page.
    """

    model = Disponibilite
    template_name = 'disponibilites/liste_disponibilites.html'
    context_object_name = 'disponibilites'

    def get_queryset(self):
        """Filtre les créneaux du médecin connecté, triés chronologiquement."""
        return Disponibilite.objects.filter(
            medecin__user=self.request.user
        ).order_by('date_disponibilite', 'heure_debut')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        disponibilites = context['disponibilites']
        # Compteurs pour les KPI du tableau de bord des créneaux
        context['libres_count']  = disponibilites.filter(
            statut_creneau=Disponibilite.StatutCreneau.LIBRE
        ).count()
        context['reserves_count'] = disponibilites.filter(
            statut_creneau=Disponibilite.StatutCreneau.RESERVE
        ).count()
        context['total_count'] = disponibilites.count()
        return context


class AjouterDisponibiliteView(MedecinRequiredMixin, View):
    """
    Crée un nouveau créneau de disponibilité pour le médecin connecté.

    On instancie Disponibilite avec le médecin et le statut LIBRE avant
    de passer au formulaire (instance=). Ainsi, ces champs sont déjà
    remplis et ne sont pas exposés dans le formulaire (pas de risque de
    manipulation côté client).

    try/except Exception : la méthode clean() du modèle peut lever une
    ValidationError si les créneaux se chevauchent. On la capture ici
    pour afficher un message d'erreur sans faire planter la vue.
    """

    def post(self, request):
        medecin  = request.user.medecin_profile
        # Pré-remplissage du médecin et du statut (non exposés dans le formulaire)
        instance = Disponibilite(medecin=medecin, statut_creneau=Disponibilite.StatutCreneau.LIBRE)
        form     = DisponibiliteForm(request.POST, instance=instance)

        if form.is_valid():
            try:
                form.save()  # appelle instance.full_clean() → instance.clean() → vérif chevauchement
                messages.success(request, 'Créneau ajouté avec succès.')
            except Exception as e:
                messages.error(request, str(e))
        else:
            # Affiche chaque erreur de validation de champ individuellement
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field} : {error}')

        return redirect('disponibilites:liste')


class ModifierDisponibiliteView(MedecinRequiredMixin, View):
    """
    Modifie un créneau existant (uniquement si statut = LIBRE).

    Contrainte métier : on ne peut pas modifier un créneau déjà réservé
    car cela impacterait le rendez-vous patient lié.
    est_libre : propriété du modèle Disponibilite (disponibilites/models.py).

    Le filtre medecin__user=request.user dans get_object_or_404 assure
    qu'un médecin ne peut pas modifier les créneaux d'un confrère
    même en devinant l'ID dans l'URL.
    """

    def post(self, request, pk):
        disponibilite = get_object_or_404(
            Disponibilite.objects.select_related('medecin__user'),
            pk=pk,
            medecin__user=request.user,  # sécurité : seulement ses propres créneaux
        )

        if not disponibilite.est_libre:
            messages.error(request, 'Seuls les créneaux libres peuvent être modifiés.')
            return redirect('disponibilites:liste')

        form = DisponibiliteForm(request.POST, instance=disponibilite)
        if form.is_valid():
            form.save()
            messages.success(request, 'Disponibilité modifiée avec succès.')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')

        return redirect('disponibilites:liste')


class SupprimerDisponibiliteView(MedecinRequiredMixin, View):
    """
    Supprime un créneau de disponibilité (uniquement si statut = LIBRE).

    On ne peut pas supprimer un créneau réservé — cela supprimerait le lien
    avec le RendezVous patient (OneToOneField avec SET_NULL, donc le RDV
    resterait sans créneau associé, mais c'est confus pour le patient).
    """

    def post(self, request, pk):
        disponibilite = get_object_or_404(
            Disponibilite.objects.select_related('medecin__user'),
            pk=pk,
            medecin__user=request.user,  # sécurité : seulement ses propres créneaux
        )

        if not disponibilite.est_libre:
            messages.error(request, 'Seuls les créneaux libres peuvent être supprimés.')
            return redirect('disponibilites:liste')

        disponibilite.delete()
        messages.success(request, 'Créneau supprimé.')
        return redirect('disponibilites:liste')
