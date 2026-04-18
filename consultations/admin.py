from django.contrib import admin

from .models import Consultation, DossierMedical


@admin.register(DossierMedical)
class DossierMedicalAdmin(admin.ModelAdmin):
    list_display = ('numero_dossier', 'patient', 'statut_dossier', 'date_ouverture', 'nombre_consultations')
    list_filter = ('statut_dossier',)
    search_fields = ('numero_dossier', 'patient__user__first_name', 'patient__user__last_name')
    readonly_fields = ('numero_dossier', 'date_ouverture')


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ('dossier', 'medecin', 'date_consultation')
    list_filter = ('date_consultation',)
    search_fields = (
        'dossier__patient__user__first_name',
        'dossier__numero_dossier',
        'medecin__user__last_name',
    )
    date_hierarchy = 'date_consultation'
    raw_id_fields = ('dossier', 'medecin', 'rendez_vous')
