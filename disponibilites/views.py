from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from .models import Disponibilite
from users.mixins import MedecinRequiredMixin


class ListeDisponibilitesView(MedecinRequiredMixin, ListView):
    model = Disponibilite
    template_name = 'disponibilites/liste_disponibilites.html'
    context_object_name = 'disponibilites'

    def get_queryset(self):
        return Disponibilite.objects.filter(
            medecin__user=self.request.user
        ).order_by('date_disponibilite', 'heure_debut')
