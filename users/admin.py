from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'role', 'statut', 'is_staff')
    list_filter = ('role', 'statut', 'is_staff', 'is_superuser')
    search_fields = ('email', 'first_name', 'last_name', 'telephone')
    ordering = ('-date_creation',)
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Profil HealthConnect', {'fields': ('role', 'telephone', 'photo', 'statut')}),
    )
