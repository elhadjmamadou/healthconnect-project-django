import uuid

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User


@receiver(post_save, sender=User)
def create_role_profile(sender, instance, created, **kwargs):
    """Crée automatiquement le profil Médecin ou Patient selon le rôle à l'inscription."""
    if not created:
        return

    if instance.role == User.Role.MEDECIN:
        from medecins.models import Medecin
        numero = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        Medecin.objects.get_or_create(user=instance, defaults={'numero_ordre': numero})

    elif instance.role == User.Role.PATIENT:
        from patients.models import Patient
        Patient.objects.get_or_create(user=instance)
