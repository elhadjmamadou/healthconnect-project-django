from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView

from users.mixins import MedecinRequiredMixin
from .models import Disponibilite


class DisponibiliteForm(forms.ModelForm):
    class Meta:
        model = Disponibilite
        fields = ['date_disponibilite', 'heure_debut', 'heure_fin', 'type_creneau']
        widgets = {
            'date_disponibilite': forms.DateInput(attrs={'type': 'date'}),
            'heure_debut': forms.TimeInput(attrs={'type': 'time'}),
            'heure_fin': forms.TimeInput(attrs={'type': 'time'}),
            'type_creneau': forms.Select(),
        }


class ListeDisponibilitesView(MedecinRequiredMixin, ListView):
    model = Disponibilite
    template_name = 'disponibilites/liste_disponibilites.html'
    context_object_name = 'disponibilites'

    def get_queryset(self):
        return Disponibilite.objects.filter(
            medecin__user=self.request.user
        ).order_by('date_disponibilite', 'heure_debut')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        disponibilites = context['disponibilites']
        context['libres_count'] = disponibilites.filter(
            statut_creneau=Disponibilite.StatutCreneau.LIBRE
        ).count()
        context['reserves_count'] = disponibilites.filter(
            statut_creneau=Disponibilite.StatutCreneau.RESERVE
        ).count()
        context['total_count'] = disponibilites.count()
        return context


class ModifierDisponibiliteView(MedecinRequiredMixin, View):
    def post(self, request, pk):
        disponibilite = get_object_or_404(
            Disponibilite.objects.select_related('medecin__user'),
            pk=pk,
            medecin__user=request.user,
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
    def post(self, request, pk):
        disponibilite = get_object_or_404(
            Disponibilite.objects.select_related('medecin__user'),
            pk=pk,
            medecin__user=request.user,
        )

        if not disponibilite.est_libre:
            messages.error(request, 'Seuls les créneaux libres peuvent être supprimés.')
            return redirect('disponibilites:liste')

        disponibilite.delete()
        messages.success(request, 'Créneau supprimé.')
        return redirect('disponibilites:liste')
