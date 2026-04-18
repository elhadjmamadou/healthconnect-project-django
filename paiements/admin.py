from django.contrib import admin

from .models import ConfigurationDjomy, Paiement


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ('reference_interne', 'montant', 'devise', 'mode_paiement', 'statut_paiement', 'date_creation')
    list_filter = ('statut_paiement', 'mode_paiement', 'devise')
    search_fields = ('reference_interne', 'reference_djomy')
    readonly_fields = ('reference_interne', 'date_creation', 'date_modification')
    raw_id_fields = ('rendez_vous', 'consultation')


@admin.register(ConfigurationDjomy)
class ConfigurationDjomyAdmin(admin.ModelAdmin):
    list_display = ('url_base', 'actif', 'date_modification')
