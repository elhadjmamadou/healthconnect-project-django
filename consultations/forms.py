from django import forms
from .models import Consultation


class ConsultationForm(forms.ModelForm):
    class Meta:
        model = Consultation
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
            'compte_rendu': 'Compte rendu',
            'diagnostic': 'Diagnostic',
            'prescription': 'Prescription',
            'observations': 'Observations',
        }
