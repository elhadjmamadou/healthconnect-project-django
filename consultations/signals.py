from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='patients.Patient')
def creer_dossier_medical(sender, instance, created, **kwargs):
    """Crée automatiquement un DossierMedical à la création d'un Patient."""
    if created:
        from consultations.models import DossierMedical
        DossierMedical.objects.get_or_create(patient=instance)


@receiver(post_save, sender='consultations.Consultation')
def marquer_rdv_termine(sender, instance, created, **kwargs):
    """Marque le rendez-vous comme terminé quand une consultation est créée."""
    if created and instance.rendez_vous:
        from rendez_vous.models import RendezVous
        instance.rendez_vous.statut_rdv = RendezVous.StatutRdv.TERMINE
        instance.rendez_vous.save(update_fields=['statut_rdv'])
