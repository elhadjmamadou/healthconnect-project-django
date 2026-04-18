from django.contrib import admin

from .models import RendezVous


@admin.register(RendezVous)
class RendezVousAdmin(admin.ModelAdmin):
    list_display = ('patient', 'medecin', 'date_rdv', 'heure_debut', 'statut_rdv', 'canal')
    list_filter = ('statut_rdv', 'canal', 'date_rdv')
    search_fields = (
        'patient__user__first_name', 'patient__user__last_name',
        'medecin__user__first_name', 'medecin__user__last_name',
    )
    date_hierarchy = 'date_rdv'
    raw_id_fields = ('patient', 'medecin', 'disponibilite')
