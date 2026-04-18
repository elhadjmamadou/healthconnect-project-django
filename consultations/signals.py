from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='patients.Patient')
def creer_dossier_medical(sender, instance, created, **kwargs):
    """Crée automatiquement un DossierMedical à la création d'un Patient."""
    if created:
        from consultations.models import DossierMedical
        DossierMedical.objects.get_or_create(patient=instance)
