from django import forms
from .models import RapportGenere


class RapportForm(forms.Form):
    type_rapport = forms.ChoiceField(
        choices=RapportGenere.TypeRapport.choices,
        label="Type de rapport",
    )
    periode_debut = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Début de période",
    )
    periode_fin = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Fin de période",
    )

    def clean(self):
        cleaned_data = super().clean()
        debut = cleaned_data.get("periode_debut")
        fin = cleaned_data.get("periode_fin")
        if debut and fin and fin <= debut:
            raise forms.ValidationError(
                "La date de fin doit être postérieure à la date de début."
            )
        return cleaned_data