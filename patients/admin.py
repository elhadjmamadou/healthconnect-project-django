from django.contrib import admin

from .models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('nom_complet', 'sexe', 'date_naissance', 'groupe_sanguin')
    list_filter = ('sexe', 'groupe_sanguin')
    search_fields = ('user__first_name', 'user__last_name', 'user__email')
    raw_id_fields = ('user',)
