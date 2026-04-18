from django.db import models


class RapportGenere(models.Model):

    class TypeRapport(models.TextChoices):
        ACTIVITE_GLOBALE = 'activite_globale', 'Activité globale'
        RENDEZ_VOUS = 'rendez_vous', 'Rendez-vous'
        PAIEMENTS = 'paiements', 'Paiements'
        MEDECINS = 'medecins', 'Médecins'
        PATIENTS = 'patients', 'Patients'

    titre = models.CharField(max_length=200, verbose_name='Titre')
    type_rapport = models.CharField(
        max_length=20,
        choices=TypeRapport.choices,
        verbose_name='Type de rapport',
    )
    periode_debut = models.DateField(verbose_name='Début de période')
    periode_fin = models.DateField(verbose_name='Fin de période')
    genere_par = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='rapports_generes',
        verbose_name='Généré par',
    )
    fichier = models.FileField(
        upload_to='rapports/',
        null=True,
        blank=True,
        verbose_name='Fichier',
    )
    date_generation = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Date de génération',
    )
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    date_modification = models.DateTimeField(auto_now=True, verbose_name='Dernière modification')

    class Meta:
        verbose_name = 'Rapport généré'
        verbose_name_plural = 'Rapports générés'
        ordering = ['-date_generation']

    def __str__(self):
        return f'{self.titre} ({self.get_type_rapport_display()}) — {self.date_generation:%d/%m/%Y}'
