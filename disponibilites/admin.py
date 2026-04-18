from django.contrib import admin

from .models import Disponibilite


@admin.register(Disponibilite)
class DisponibiliteAdmin(admin.ModelAdmin):
    list_display = ('medecin', 'date_disponibilite', 'heure_debut', 'heure_fin', 'statut_creneau', 'type_creneau')
    list_filter = ('statut_creneau', 'type_creneau', 'date_disponibilite')
    search_fields = ('medecin__user__first_name', 'medecin__user__last_name')
    date_hierarchy = 'date_disponibilite'
