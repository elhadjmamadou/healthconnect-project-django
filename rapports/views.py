from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.files.base import ContentFile
from django.db.models import Sum
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.generic import FormView, ListView, View

from weasyprint import HTML

from medecins.models import Medecin
from paiements.models import Paiement
from patients.models import Patient
from rendez_vous.models import RendezVous

from .forms import RapportForm
from .models import RapportGenere


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