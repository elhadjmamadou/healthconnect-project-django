# ==============================================================================
# rapports/models.py — Modèle RapportGenere
# ==============================================================================
# Ce modèle représente un rapport statistique généré par un administrateur.
# Un rapport est défini par un type (activité globale, RDV, paiements…)
# et une période (date début → date fin).
#
# Cycle de vie d'un rapport :
#   1. L'admin choisit le type et la période dans le formulaire (rapports/forms.py)
#   2. La vue GenererRapportView calcule les statistiques depuis la BDD
#   3. Un objet RapportGenere est créé avec un éventuel fichier exporté
#   4. L'admin peut télécharger ou supprimer le rapport depuis la liste
#
# On_delete=SET_NULL sur genere_par : si le compte admin est supprimé,
# les rapports restent en base mais genere_par devient NULL.
# On ne supprime pas les rapports par cascade car ils ont une valeur historique.
# ==============================================================================

from django.db import models


class RapportGenere(models.Model):
    """
    Rapport statistique généré par un administrateur.

    TypeRapport (TextChoices) : chaque valeur correspond à une section
    du dashboard admin et à une logique de calcul différente dans rapports/views.py.

    fichier (FileField) : chemin vers le fichier exporté (PDF, CSV…) dans MEDIA_ROOT.
      upload_to='rapports/' → les fichiers sont stockés dans MEDIA_ROOT/rapports/
      null=True, blank=True → un rapport peut n'avoir aucun fichier (consultation en ligne)

    date_generation vs date_creation : les deux utilisent auto_now_add=True.
    Fonctionnellement identiques ici (créés au même moment), mais séparés pour
    permettre d'ajouter une logique de "re-génération" à l'avenir sans migration.

    ordering = ['-date_generation'] : les rapports sont triés du plus récent au plus ancien.
    """

    class TypeRapport(models.TextChoices):
        # Chaque choix : (valeur_BDD, label_affiché)
        ACTIVITE_GLOBALE = 'activite_globale', 'Activité globale'   # KPIs globaux de la plateforme
        RENDEZ_VOUS      = 'rendez_vous',      'Rendez-vous'         # statistiques des RDV
        PAIEMENTS        = 'paiements',        'Paiements'           # revenus et transactions
        MEDECINS         = 'medecins',         'Médecins'            # activité des médecins
        PATIENTS         = 'patients',         'Patients'            # démographie des patients

    titre = models.CharField(max_length=200, verbose_name='Titre')

    type_rapport = models.CharField(
        max_length=20,
        choices=TypeRapport.choices,  # liste déroulante dans l'admin Django
        verbose_name='Type de rapport',
    )

    periode_debut = models.DateField(verbose_name='Début de période')
    periode_fin   = models.DateField(verbose_name='Fin de période')

    genere_par = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,  # si l'admin est supprimé → genere_par = NULL (pas de cascade)
        null=True,
        related_name='rapports_generes',  # user.rapports_generes.all() pour l'historique de l'admin
        verbose_name='Généré par',
    )

    fichier = models.FileField(
        upload_to='rapports/',   # fichiers dans MEDIA_ROOT/rapports/
        null=True,
        blank=True,              # optionnel : un rapport peut n'avoir aucun fichier exporté
        verbose_name='Fichier',
    )

    # auto_now_add=True : rempli automatiquement à la création, non modifiable ensuite
    date_generation  = models.DateTimeField(auto_now_add=True, verbose_name='Date de génération')
    date_creation    = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    date_modification = models.DateTimeField(auto_now=True,     verbose_name='Dernière modification')

    class Meta:
        verbose_name        = 'Rapport généré'
        verbose_name_plural = 'Rapports générés'
        ordering            = ['-date_generation']  # du plus récent au plus ancien

    def __str__(self):
        # Exemple : "Activité janvier 2025 (Activité globale) — 15/01/2025"
        return f'{self.titre} ({self.get_type_rapport_display()}) — {self.date_generation:%d/%m/%Y}'
