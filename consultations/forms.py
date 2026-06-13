# ==============================================================================
# consultations/forms.py — Formulaire de compte-rendu de consultation
# ==============================================================================
# Un seul formulaire ici : ConsultationForm, utilisé par le médecin pour
# rédiger le compte-rendu médical après avoir reçu un patient.
#
# ModelForm : Django génère automatiquement les champs depuis le modèle
# Consultation et gère la validation + sauvegarde en base de données.
# ==============================================================================

from django import forms
from .models import Consultation


class ConsultationForm(forms.ModelForm):
    """
    Formulaire de rédaction d'un compte-rendu de consultation.

    Champs exposés au médecin :
      compte_rendu  : résumé de la consultation
      diagnostic    : diagnostic médical posé
      prescription  : médicaments prescrits (texte libre, complété par l'ordonnance)
      observations  : notes complémentaires du médecin

    widgets{} : personnalise le widget HTML pour chaque champ.
    On utilise Textarea avec des placeholders descriptifs pour guider le médecin.
    La classe CSS 'form-textarea' est définie dans custom.css pour assurer
    un style cohérent avec le reste de l'interface sombre.

    Les champs non listés dans fields (date_consultation, dossier, medecin…)
    sont remplis automatiquement dans CreerConsultationView.form_valid()
    avec commit=False, avant la sauvegarde finale.
    """

    class Meta:
        model  = Consultation
        fields = ('compte_rendu', 'diagnostic', 'prescription', 'observations')
        widgets = {
            'compte_rendu': forms.Textarea(attrs={
                'placeholder': 'Décrivez le compte rendu de la consultation...',
                'rows': 5,
                'class': 'form-textarea'
            }),
            'diagnostic': forms.Textarea(attrs={
                'placeholder': 'Inscrivez votre diagnostic...',
                'rows': 4,
                'class': 'form-textarea'
            }),
            'prescription': forms.Textarea(attrs={
                'placeholder': 'Indiquez les prescriptions médicales...',
                'rows': 4,
                'class': 'form-textarea'
            }),
            'observations': forms.Textarea(attrs={
                'placeholder': 'Ajoutez vos observations supplémentaires...',
                'rows': 3,
                'class': 'form-textarea'
            }),
        }
        labels = {
            'compte_rendu':  'Compte rendu',
            'diagnostic':    'Diagnostic',
            'prescription':  'Prescription',
            'observations':  'Observations',
        }
