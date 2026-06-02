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
    template_name = "rapports/dashboard_admin.html"

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_admin_role

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        debut_mois = today.replace(day=1)

        revenus_mois = (
            Paiement.objects.filter(
                statut_paiement=Paiement.StatutPaiement.CONFIRME,
                date_paiement__date__gte=debut_mois,
            ).aggregate(total=Sum("montant"))["total"]
            or 0
        )

        context["stats"] = {
            "total_patients": Patient.objects.count(),
            "patients_new_month": Patient.objects.filter(
                date_creation__date__gte=debut_mois
            ).count(),
            "total_medecins": Medecin.objects.count(),
            "rdv_today": RendezVous.objects.filter(date_rdv=today).count(),
            "revenus_mois": f"{revenus_mois:,.0f}",
        }

        context["rdv_recents"] = RendezVous.objects.select_related(
            "patient__user", "medecin__user"
        ).order_by("-date_creation")[:6]

        medecins_qs = list(
            Medecin.objects.annotate(nb_rdv=Count("rendez_vous")).order_by("-nb_rdv")[:5]
        )
        max_rdv = medecins_qs[0].nb_rdv if medecins_qs else 1
        for m in medecins_qs:
            m.pct = round(m.nb_rdv / max_rdv * 100) if max_rdv else 0
        context["top_medecins"] = medecins_qs

        context["notifications_recentes"] = Notification.objects.select_related(
            "utilisateur"
        ).order_by("-date_envoi")[:6]

        labels, values = [], []
        for i in range(29, -1, -1):
            day = today - timedelta(days=i)
            labels.append(day.strftime("%d/%m"))
            values.append(RendezVous.objects.filter(date_rdv=day).count())
        context["rdv_chart_data"] = json.dumps({"labels": labels, "values": values})

        specialites = Specialite.objects.annotate(
            nb_medecins=Count("medecins")
        ).filter(nb_medecins__gt=0).order_by("-nb_medecins")[:6]
        context["specialites_chart_data"] = json.dumps({
            "labels": [s.libelle for s in specialites],
            "values": [s.nb_medecins for s in specialites],
        })

        return context


def collecter_statistiques(debut, fin):
    """Compte les données de la clinique sur la période choisie."""
    rdv = RendezVous.objects.filter(date_rdv__range=(debut, fin))
    paiements = Paiement.objects.filter(
        statut_paiement=Paiement.StatutPaiement.CONFIRME,
        date_paiement__date__range=(debut, fin),
    )
    return {
        "rdv_total": rdv.count(),
        "rdv_confirmes": rdv.filter(statut_rdv=RendezVous.StatutRdv.CONFIRME).count(),
        "rdv_termines": rdv.filter(statut_rdv=RendezVous.StatutRdv.TERMINE).count(),
        "rdv_en_attente": rdv.filter(statut_rdv=RendezVous.StatutRdv.EN_ATTENTE).count(),
        "rdv_annules": rdv.filter(
            statut_rdv__in=[
                RendezVous.StatutRdv.ANNULE_PATIENT,
                RendezVous.StatutRdv.ANNULE_MEDECIN,
            ]
        ).count(),
        "rdv_no_show": rdv.filter(statut_rdv=RendezVous.StatutRdv.NO_SHOW).count(),
        "ca_total": paiements.aggregate(total=Sum("montant"))["total"] or 0,
        "paiements_count": paiements.count(),
        "nb_medecins": Medecin.objects.count(),
        "nb_patients": Patient.objects.count(),
        "nouveaux_medecins": Medecin.objects.filter(
            date_creation__date__range=(debut, fin)
        ).count(),
        "nouveaux_patients": Patient.objects.filter(
            date_creation__date__range=(debut, fin)
        ).count(),
    }


class ListeRapportsView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = RapportGenere
    template_name = "rapports/liste_rapports.html"
    context_object_name = "rapports"
    paginate_by = 10

    def test_func(self):
        return self.request.user.is_staff

    def get_queryset(self):
        qs = super().get_queryset()
        type_filtre = self.request.GET.get("type")
        debut = self.request.GET.get("debut")
        fin = self.request.GET.get("fin")
        if type_filtre:
            qs = qs.filter(type_rapport=type_filtre)
        if debut:
            qs = qs.filter(periode_debut__gte=debut)
        if fin:
            qs = qs.filter(periode_fin__lte=fin)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["types"] = RapportGenere.TypeRapport.choices
        context["type_actif"] = self.request.GET.get("type", "")
        context["debut_actif"] = self.request.GET.get("debut", "")
        context["fin_actif"] = self.request.GET.get("fin", "")
        return context


class GenererRapportView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = "rapports/generer_rapport.html"
    form_class = RapportForm

    def test_func(self):
        return self.request.user.is_staff

    def form_valid(self, form):
        type_rapport = form.cleaned_data["type_rapport"]
        debut = form.cleaned_data["periode_debut"]
        fin = form.cleaned_data["periode_fin"]

        libelle = dict(RapportGenere.TypeRapport.choices)[type_rapport]
        titre = f"{libelle} — du {debut:%d/%m/%Y} au {fin:%d/%m/%Y}"

        stats = collecter_statistiques(debut, fin)

        html = render_to_string(
            "rapports/pdf/rapport_activite.html",
            {
                "titre": titre,
                "libelle": libelle,
                "debut": debut,
                "fin": fin,
                "stats": stats,
                "genere_par": self.request.user,
                "date_generation": timezone.now(),
            },
        )
        pdf = HTML(string=html).write_pdf()

        rapport = RapportGenere(
            titre=titre,
            type_rapport=type_rapport,
            periode_debut=debut,
            periode_fin=fin,
            genere_par=self.request.user,
        )
        nom_fichier = f"rapport_{type_rapport}_{debut:%Y%m%d}_{fin:%Y%m%d}.pdf"
        rapport.fichier.save(nom_fichier, ContentFile(pdf), save=False)
        rapport.save()

        messages.success(self.request, "Rapport généré avec succès.")
        return redirect("rapports:liste")


class TelechargerRapportView(LoginRequiredMixin, UserPassesTestMixin, View):
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
    def test_func(self):
        return self.request.user.is_staff

    def post(self, request, pk):
        rapport = get_object_or_404(RapportGenere, pk=pk)
        if rapport.fichier:
            rapport.fichier.delete(save=False)  # supprime aussi le fichier du disque
        rapport.delete()
        messages.success(request, "Rapport supprimé.")
        return redirect("rapports:liste")