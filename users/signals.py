import uuid

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User


@receiver(post_save, sender=User)
def create_medecin_profile(sender, instance, created, **kwargs):
    if created and instance.role == User.Role.MEDECIN:
        from medecins.models import Medecin
        numero = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        Medecin.objects.create(user=instance, numero_ordre=numero)
