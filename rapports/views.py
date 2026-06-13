# ==============================================================================
# rapports/views.py — Dashboard admin et génération de rapports PDF
# ==============================================================================
# Ce fichier contient la logique la plus complexe du projet :
#
# DashboardAdminView : tableau de bord en temps réel avec 4 types de graphiques.
#   Les données sont agrégées via des requêtes Django avancées (TruncDate,
#   TruncMonth, annotate, aggregate) et passées à Chart.js en JSON.
#
# collecter_statistiques() : fonction utilitaire qui produit les KPI
#   pour les rapports PDF périodiques.
#
# GenererRapportView : génère un PDF de rapport d'activité via WeasyPrint
#   et le stocke sur le disque (champ FileField).
# ==============================================================================

import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.files.base import ContentFile
from django.db.models import Count, Sum
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.generic import FormView, ListView, TemplateView, View

from weasyprint import HTML

from medecins.models import Medecin, Specialite
from notifications.models import Notification
from paiements.models import Paiement
from patients.models import Patient
from rendez_vous.models import RendezVous

from .forms import RapportForm
from .models import RapportGenere


class DashboardAdminView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    Tableau de bord de l'administrateur — vue la plus riche du projet.

    UserPassesTestMixin + test_func() : accès réservé aux staff et admin.
    TemplateView : vue simple qui appelle get_context_data() et rend un template.

    Le dashboard affiche :
      - 4 KPI (patients, médecins, RDV aujourd'hui, revenus du mois)
      - Graphe combiné "Pouls de la plateforme" (barres RDV + courbe revenus par jour)
      - Graphe doughnut des statuts de RDV (toute la période)
      - Graphe barres des nouveaux patients (par mois)
      - Graphe polar area des spécialités (répartition des médecins)
      - Timeline des RDV récents et des notifications
    """

    template_name = "rapports/dashboard_admin.html"

    def test_func(self):
        """Condition d'accès : staff Django ou rôle admin applicatif."""
        return self.request.user.is_staff or self.request.user.is_admin_role

    # Noms des mois en français abrégés — indexés de 0 à 11 (MOIS_FR[0] = 'Jan')
    MOIS_FR = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin',
               'Juil', 'Août', 'Sep', 'Oct', 'Nov', 'Déc']

    def get_context_data(self, **kwargs):
        """
        Construit toutes les données du dashboard en une seule méthode.

        Techniques Django avancées utilisées ici :
          - TruncDate / TruncMonth : fonctions SQL de troncature temporelle
          - annotate()   : ajoute un champ calculé à chaque objet du queryset
          - aggregate()  : calcule une valeur unique sur tout le queryset (SUM, COUNT…)
          - values_list() + dict() : transforme un queryset en dictionnaire {clé: valeur}
        """
        from django.db.models.functions import TruncDate, TruncMonth

        context = super().get_context_data(**kwargs)
        today           = timezone.now().date()
        debut_mois      = today.replace(day=1)                           # 1er du mois courant
        debut_mois_prec = (debut_mois - timedelta(days=1)).replace(day=1)  # 1er du mois précédent
        il_y_a_30j      = today - timedelta(days=29)

        # ==================================================================
        # KPI — Indicateurs clés de performance
        # ==================================================================

        # Queryset de base : tous les paiements confirmés (réutilisé plusieurs fois)
        paiements_confirmes = Paiement.objects.filter(
            statut_paiement=Paiement.StatutPaiement.CONFIRME
        )

        # Revenus du mois courant (somme des montants confirmés depuis le 1er)
        revenus_mois = (
            paiements_confirmes.filter(date_paiement__date__gte=debut_mois)
            .aggregate(total=Sum("montant"))["total"] or 0
        )

        # Revenus du mois précédent (pour calculer la variation en %)
        revenus_mois_prec = (
            paiements_confirmes.filter(
                date_paiement__date__gte=debut_mois_prec,
                date_paiement__date__lt=debut_mois,
            ).aggregate(total=Sum("montant"))["total"] or 0
        )

        # Calcul du delta en % : (nouveau - ancien) / ancien * 100
        # None si le mois précédent est à 0 (division par zéro impossible)
        if revenus_mois_prec:
            revenus_delta = round((revenus_mois - revenus_mois_prec) / revenus_mois_prec * 100)
        else:
            revenus_delta = None

        rdv_today = RendezVous.objects.filter(date_rdv=today).count()
        rdv_hier  = RendezVous.objects.filter(date_rdv=today - timedelta(days=1)).count()

        context["stats"] = {
            "total_patients":    Patient.objects.count(),
            "patients_new_month": Patient.objects.filter(date_creation__date__gte=debut_mois).count(),
            "total_medecins":    Medecin.objects.count(),
            "medecins_new_month": Medecin.objects.filter(date_creation__date__gte=debut_mois).count(),
            "rdv_today":         rdv_today,
            "rdv_delta_hier":    rdv_today - rdv_hier,  # positif = plus qu'hier, négatif = moins
            # Formatage du montant avec séparateur espace (30 000 GNF au lieu de 30000)
            "revenus_mois":      f"{revenus_mois:,.0f}".replace(",", " "),
            "revenus_delta":     revenus_delta,
        }

        # RDV récents pour la timeline
        context["rdv_recents"] = RendezVous.objects.select_related(
            "patient__user", "medecin__user"
        ).order_by("-date_creation")[:6]

        # Top 5 médecins par nombre de RDV (avec barre de progression)
        medecins_qs = list(
            Medecin.objects.select_related("user")
            .prefetch_related("specialites")
            .annotate(nb_rdv=Count("rendez_vous"))  # champ calculé pour chaque médecin
            .order_by("-nb_rdv")[:5]
        )
        max_rdv = medecins_qs[0].nb_rdv if medecins_qs else 1
        for m in medecins_qs:
            # Calcul du pourcentage pour la barre de progression CSS
            m.pct = round(m.nb_rdv / max_rdv * 100) if max_rdv else 0
        context["top_medecins"] = medecins_qs

        context["notifications_recentes"] = Notification.objects.select_related(
            "utilisateur"
        ).order_by("-date_envoi")[:6]

        # ==================================================================
        # GRAPHE 1 : Activité quotidienne — RDV et revenus par jour
        # ==================================================================
        # Stratégie : on détecte automatiquement la période des données réelles.
        # Si des données existent → fenêtre de min(première date) à max(dernière date).
        # Si aucune donnée → fallback sur les 30 derniers jours.
        # Plafond à 365 jours pour éviter un graphe illisible sur des projets anciens.

        # Transformation du queryset en dict {date: count} en une seule requête
        # values_list("date_rdv") + annotate(c=Count("id")) → SELECT date_rdv, COUNT(id)
        rdv_par_jour = dict(
            RendezVous.objects.values_list("date_rdv").annotate(c=Count("id"))
        )

        # Revenus journaliers — TruncDate("date_paiement") tronque datetime → date
        # Permet de grouper plusieurs paiements du même jour
        revenus_par_jour = {
            row["jour"]: float(row["total"])
            for row in paiements_confirmes
            .annotate(jour=TruncDate("date_paiement"))
            .values("jour")
            .annotate(total=Sum("montant"))
        }

        # Détermination de la fenêtre temporelle du graphe
        toutes_dates = list(rdv_par_jour) + list(revenus_par_jour)
        if toutes_dates:
            debut_serie = min(toutes_dates)                     # date du premier événement
            fin_serie   = max(max(toutes_dates), today)         # date du dernier (ou aujourd'hui)
        else:
            debut_serie, fin_serie = il_y_a_30j, today          # fallback 30 jours

        # Plafond à 365 jours pour la lisibilité
        if (fin_serie - debut_serie).days > 365:
            debut_serie = fin_serie - timedelta(days=365)

        # Construction des 3 listes parallèles pour Chart.js :
        # labels = dates, rdv_values = nb RDV, revenus_values = montant revenus
        labels, rdv_values, revenus_values = [], [], []
        day = debut_serie
        while day <= fin_serie:
            labels.append(day.strftime("%d/%m"))
            rdv_values.append(rdv_par_jour.get(day, 0))          # 0 si pas de RDV ce jour-là
            revenus_values.append(revenus_par_jour.get(day, 0))  # 0 si pas de revenus
            day += timedelta(days=1)

        context["activite_chart_data"] = {
            "labels":   labels,
            "rdv":      rdv_values,
            "revenus":  revenus_values,
        }
        context["activite_periode"] = f"du {debut_serie:%d/%m/%Y} au {fin_serie:%d/%m/%Y}"

        # ==================================================================
        # GRAPHE 2 : Répartition des statuts de RDV (Doughnut Chart.js)
        # ==================================================================
        # On agrège les RDV par statut sur TOUTE la période (pas de filtre de date)
        # Résultat : dict {"confirme": 42, "en_attente": 7, "termine": 100, ...}
        statuts = dict(
            RendezVous.objects.values_list("statut_rdv").annotate(c=Count("id"))
        )
        context["statuts_chart_data"] = {
            "labels": ["Confirmés", "En attente", "Terminés", "Annulés", "Non présentés"],
            "values": [
                statuts.get("confirme", 0),
                statuts.get("en_attente", 0),
                statuts.get("termine", 0),
                # Annulés = annulé patient + annulé médecin (cumulés)
                statuts.get("annule_patient", 0) + statuts.get("annule_medecin", 0),
                statuts.get("no_show", 0),
            ],
        }

        # ==================================================================
        # GRAPHE 3 : Nouveaux patients par mois (Bar Chart.js)
        # ==================================================================
        # TruncMonth("date_creation") : tronque la date à l'année+mois
        # → permet de grouper tous les patients créés en janvier 2025 ensemble
        #
        # hasattr(row["mois"], "date") : certaines BDD retournent un datetime,
        # d'autres une date — on normalise en date pour la comparaison

        patients_par_mois = {
            row["mois"].date() if hasattr(row["mois"], "date") else row["mois"]: row["c"]
            for row in Patient.objects
            .annotate(mois=TruncMonth("date_creation"))
            .values("mois")
            .annotate(c=Count("id"))
        }

        # Début de la série : 1er patient inscrit ou il y a 12 mois max
        if patients_par_mois:
            debut_periode = min(patients_par_mois)
        else:
            debut_periode = debut_mois

        # Plancher : on recule au maximum de 335 jours (≈ 11 mois) depuis le 1er du mois
        plancher = (debut_mois - timedelta(days=335)).replace(day=1)
        debut_periode = max(debut_periode, plancher)

        # Itération mois par mois jusqu'à aujourd'hui
        mois_labels, mois_values = [], []
        annee, mois = debut_periode.year, debut_periode.month
        while (annee, mois) <= (today.year, today.month):
            # Clé de recherche dans patients_par_mois (date normalisée au 1er du mois)
            cle = today.replace(year=annee, month=mois, day=1)

            label = self.MOIS_FR[mois - 1]  # ex : 'Jan' pour mois=1
            # Si la série couvre plusieurs années, on ajoute l'année pour disambiguïser
            if annee != today.year:
                label += f" {annee % 100}"  # ex : 'Jan 24' pour janvier 2024

            mois_labels.append(label)
            mois_values.append(patients_par_mois.get(cle, 0))

            # Incrémentation du mois avec passage en fin d'année
            annee, mois = (annee + 1, 1) if mois == 12 else (annee, mois + 1)

        context["patients_chart_data"] = {
            "labels": mois_labels,
            "values": mois_values,
        }

        # ==================================================================
        # GRAPHE 4 : Répartition des spécialités (Polar Area Chart.js)
        # ==================================================================
        # Affiche le top 6 des spécialités par nombre de médecins.
        # filter(nb_medecins__gt=0) : exclut les spécialités sans médecin.
        specialites = Specialite.objects.annotate(
            nb_medecins=Count("medecins")
        ).filter(nb_medecins__gt=0).order_by("-nb_medecins")[:6]

        context["specialites_chart_data"] = {
            "labels": [s.libelle for s in specialites],
            "values": [s.nb_medecins for s in specialites],
        }

        return context


def collecter_statistiques(debut, fin):
    """
    Calcule les statistiques d'activité sur une période donnée.

    Utilisée par GenererRapportView pour remplir le template PDF.
    Regroupe les métriques clés : RDV (par statut), chiffre d'affaires,
    paiements, médecins et patients.

    Args:
        debut (date): Première date de la période.
        fin (date):   Dernière date de la période.

    Returns:
        dict: Dictionnaire de KPI prêt à être passé au template PDF.
    """
    rdv = RendezVous.objects.filter(date_rdv__range=(debut, fin))
    paiements = Paiement.objects.filter(
        statut_paiement=Paiement.StatutPaiement.CONFIRME,
        date_paiement__date__range=(debut, fin),
    )
    return {
        "rdv_total":       rdv.count(),
        "rdv_confirmes":   rdv.filter(statut_rdv=RendezVous.StatutRdv.CONFIRME).count(),
        "rdv_termines":    rdv.filter(statut_rdv=RendezVous.StatutRdv.TERMINE).count(),
        "rdv_en_attente":  rdv.filter(statut_rdv=RendezVous.StatutRdv.EN_ATTENTE).count(),
        "rdv_annules":     rdv.filter(
            statut_rdv__in=[
                RendezVous.StatutRdv.ANNULE_PATIENT,
                RendezVous.StatutRdv.ANNULE_MEDECIN,
            ]
        ).count(),
        "rdv_no_show":      rdv.filter(statut_rdv=RendezVous.StatutRdv.NO_SHOW).count(),
        "ca_total":         paiements.aggregate(total=Sum("montant"))["total"] or 0,
        "paiements_count":  paiements.count(),
        "nb_medecins":      Medecin.objects.count(),
        "nb_patients":      Patient.objects.count(),
        "nouveaux_medecins": Medecin.objects.filter(date_creation__date__range=(debut, fin)).count(),
        "nouveaux_patients": Patient.objects.filter(date_creation__date__range=(debut, fin)).count(),
    }


class ListeRapportsView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Liste les rapports PDF générés (staff seulement)."""

    model = RapportGenere
    template_name = "rapports/liste_rapports.html"
    context_object_name = "rapports"
    paginate_by = 10

    def test_func(self):
        return self.request.user.is_staff

    def get_queryset(self):
        """Filtre les rapports par type et/ou période."""
        qs        = super().get_queryset()
        type_filtre = self.request.GET.get("type")
        debut     = self.request.GET.get("debut")
        fin       = self.request.GET.get("fin")
        if type_filtre:
            qs = qs.filter(type_rapport=type_filtre)
        if debut:
            qs = qs.filter(periode_debut__gte=debut)
        if fin:
            qs = qs.filter(periode_fin__lte=fin)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["types"]       = RapportGenere.TypeRapport.choices
        context["type_actif"]  = self.request.GET.get("type", "")
        context["debut_actif"] = self.request.GET.get("debut", "")
        context["fin_actif"]   = self.request.GET.get("fin", "")
        return context


class GenererRapportView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    """
    Génère un rapport PDF d'activité pour une période choisie.

    Étapes :
      1. L'admin remplit le formulaire (type, période)
      2. form_valid() collecte les statistiques via collecter_statistiques()
      3. WeasyPrint convertit le template HTML en PDF (bytes en mémoire)
      4. Le PDF est sauvegardé sur le disque via rapport.fichier.save()
      5. L'objet RapportGenere est créé en base avec un lien vers le fichier

    ContentFile(pdf) : enveloppe les bytes du PDF dans un objet fichier
    compatible avec l'API de stockage Django (FileField).
    """

    template_name = "rapports/generer_rapport.html"
    form_class    = RapportForm

    def test_func(self):
        return self.request.user.is_staff

    def form_valid(self, form):
        type_rapport = form.cleaned_data["type_rapport"]
        debut        = form.cleaned_data["periode_debut"]
        fin          = form.cleaned_data["periode_fin"]

        libelle = dict(RapportGenere.TypeRapport.choices)[type_rapport]
        titre   = f"{libelle} — du {debut:%d/%m/%Y} au {fin:%d/%m/%Y}"

        stats = collecter_statistiques(debut, fin)

        # Rendu du template HTML avec les statistiques
        html = render_to_string(
            "rapports/pdf/rapport_activite.html",
            {
                "titre":          titre,
                "libelle":        libelle,
                "debut":          debut,
                "fin":            fin,
                "stats":          stats,
                "genere_par":     self.request.user,
                "date_generation": timezone.now(),
            },
        )

        # Conversion HTML → PDF en mémoire par WeasyPrint
        pdf = HTML(string=html).write_pdf()

        rapport = RapportGenere(
            titre=titre,
            type_rapport=type_rapport,
            periode_debut=debut,
            periode_fin=fin,
            genere_par=self.request.user,
        )

        # Sauvegarde du PDF sur le système de fichiers (MEDIA_ROOT/rapports/)
        # save=False : on ne sauvegarde pas le RapportGenere encore (on appelle .save() ensuite)
        nom_fichier = f"rapport_{type_rapport}_{debut:%Y%m%d}_{fin:%Y%m%d}.pdf"
        rapport.fichier.save(nom_fichier, ContentFile(pdf), save=False)
        rapport.save()   # INSERT final en base de données

        messages.success(self.request, "Rapport généré avec succès.")
        return redirect("rapports:liste")


class TelechargerRapportView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Télécharge un rapport PDF existant.

    FileResponse : gère le streaming du fichier, plus efficace qu'HttpResponse
    pour les gros fichiers car il ne charge pas tout le fichier en mémoire.
    as_attachment=True : force le téléchargement plutôt que l'ouverture inline.
    """

    def test_func(self):
        return self.request.user.is_staff

    def get(self, request, pk):
        rapport = get_object_or_404(RapportGenere, pk=pk)
        if not rapport.fichier:
            raise Http404("Ce rapport n'a pas de fichier PDF.")
        return FileResponse(
            rapport.fichier.open("rb"),
            content_type="application/pdf",
            as_attachment=True,
            filename=rapport.fichier.name.split("/")[-1],
        )


class SupprimerRapportView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Supprime un rapport et son fichier PDF du disque."""

    def test_func(self):
        return self.request.user.is_staff

    def post(self, request, pk):
        rapport = get_object_or_404(RapportGenere, pk=pk)
        if rapport.fichier:
            # delete(save=False) : supprime le fichier physique sans re-sauvegarder l'objet
            rapport.fichier.delete(save=False)
        rapport.delete()
        messages.success(request, "Rapport supprimé.")
        return redirect("rapports:liste")
