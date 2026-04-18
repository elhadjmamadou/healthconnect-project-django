from django.contrib import admin

from .models import Medecin, Specialite


@admin.register(Specialite)
class SpecialiteAdmin(admin.ModelAdmin):
    list_display = ('libelle', 'icone')
    search_fields = ('libelle',)


@admin.register(Medecin)
class MedecinAdmin(admin.ModelAdmin):
    list_display = ('nom_complet', 'numero_ordre', 'mode_exercice', 'tarif_consultation', 'accepte_nouveaux_patients')
    list_filter = ('mode_exercice', 'accepte_nouveaux_patients', 'specialites')
    search_fields = ('user__first_name', 'user__last_name', 'numero_ordre')
    filter_horizontal = ('specialites',)
    raw_id_fields = ('user',)
