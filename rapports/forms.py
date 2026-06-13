# ==============================================================================
# rapports/forms.py — Formulaire de génération de rapport statistique
# ==============================================================================
# RapportForm hérite de forms.Form (pas forms.ModelForm).
# Pourquoi ? Ce formulaire ne crée pas directement un objet RapportGenere.
# Il sert juste à collecter les paramètres de la requête (type + période).
# La vue GenererRapportView lit ces données, calcule les stats, puis crée
# éventuellement un RapportGenere avec les résultats.
#
# Validation personnalisée :
# clean() est la méthode de validation globale du formulaire (après que
# chaque champ individuel a été validé). Elle vérifie la cohérence entre
# plusieurs champs : ici, que la date de fin est bien APRÈS la date de début.
# ==============================================================================

from django import forms
from .models import RapportGenere


class RapportForm(forms.Form):
    """
    Formulaire de sélection du type de rapport et de la période d'analyse.

    forms.Form (pas ModelForm) : pas de liaison directe avec un modèle.
    Les données sont utilisées comme paramètres de calcul, pas pour un INSERT.

    type_rapport : ChoiceField alimenté par RapportGenere.TypeRapport.choices
    → génère un <select> avec les 5 types de rapport disponibles.

    periode_debut / periode_fin : DateField avec widget HTML5 type="date"
    → sélecteur de date natif du navigateur, sans JavaScript supplémentaire.
    """

    type_rapport = forms.ChoiceField(
        choices=RapportGenere.TypeRapport.choices,  # liste des 5 types de rapport
        label="Type de rapport",
    )

    periode_debut = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),  # sélecteur natif HTML5
        label="Début de période",
    )

    periode_fin = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),  # sélecteur natif HTML5
        label="Fin de période",
    )

    def clean(self):
        """
        Validation croisée : vérifie que la date de fin est postérieure au début.

        clean() est appelée par Django APRÈS la validation de chaque champ individuel.
        cleaned_data contient uniquement les champs qui ont passé leur validation
        individuelle → on vérifie l'existence (get()) avant de comparer.

        fin <= debut : on refuse aussi les périodes de 0 jour (fin == debut)
        car les graphiques seraient vides et non significatifs.

        raise forms.ValidationError() : l'erreur est attachée au formulaire global
        (pas à un champ spécifique) et affichée dans {{ form.non_field_errors }}.
        """
        cleaned_data = super().clean()
        debut = cleaned_data.get("periode_debut")
        fin   = cleaned_data.get("periode_fin")

        if debut and fin and fin <= debut:
            # Erreur globale (non attachée à un seul champ)
            raise forms.ValidationError(
                "La date de fin doit être postérieure à la date de début."
            )

        return cleaned_data
