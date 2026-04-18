from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='rendez_vous.RendezVous')
def sync_disponibilite_statut(sender, instance, **kwargs):
    """Met à jour le statut du créneau de disponibilité lié au rendez-vous."""
    if not instance.disponibilite_id:
        return

    from disponibilites.models import Disponibilite

    statuts_annules = [
        'annule_patient',
        'annule_medecin',
        'no_show',
    ]
    statuts_actifs = ['en_attente', 'confirme']

    if instance.statut_rdv in statuts_actifs:
        nouveau_statut = Disponibilite.StatutCreneau.RESERVE
    elif instance.statut_rdv in statuts_annules:
        nouveau_statut = Disponibilite.StatutCreneau.LIBRE
    else:
        return

    Disponibilite.objects.filter(pk=instance.disponibilite_id).update(
        statut_creneau=nouveau_statut
    )
