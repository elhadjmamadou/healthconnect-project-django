from django.contrib import admin

from .models import RapportGenere


@admin.register(RapportGenere)
class RapportGenereAdmin(admin.ModelAdmin):
    list_display = ('titre', 'type_rapport', 'periode_debut', 'periode_fin', 'genere_par', 'date_generation')
    list_filter = ('type_rapport',)
    search_fields = ('titre', 'genere_par__email')
    readonly_fields = ('date_generation',)
    raw_id_fields = ('genere_par',)
