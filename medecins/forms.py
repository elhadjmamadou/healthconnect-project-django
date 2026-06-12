from django import forms
from django.contrib.auth.forms import UserCreationForm

from users.models import User
from .models import Medecin, Specialite


class CreerMedecinUserForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'telephone')
        labels = {
            'first_name': 'Prénom',
            'last_name': 'Nom',
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email
        user.role = User.Role.MEDECIN
        if commit:
            user.save()
        return user


class MedecinProfileForm(forms.ModelForm):
    specialites = forms.ModelMultipleChoiceField(
        queryset=Specialite.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Spécialités',
    )

    class Meta:
        model = Medecin
        fields = ('numero_ordre', 'biographie', 'tarif_consultation', 'mode_exercice', 'specialites', 'accepte_nouveaux_patients')
        widgets = {
            'biographie': forms.Textarea(attrs={'rows': 4}),
        }


class ModifierMedecinUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'telephone', 'statut')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email
        if commit:
            user.save()
        return user


class SpecialiteForm(forms.ModelForm):

    INPUT_CLASSES = (
        'w-full bg-background border border-outline-variant/50 rounded-xl '
        'px-4 py-3 text-sm text-on-surface placeholder:text-on-surface-variant/40'
    )

    class Meta:
        model = Specialite
        fields = ('libelle', 'description', 'icone')
        widgets = {
            'libelle': forms.TextInput(attrs={
                'placeholder': 'Ex : Cardiologie',
            }),
            'icone': forms.TextInput(attrs={
                'placeholder': 'Ex : stethoscope',
            }),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Brève description de la spécialité…',
            }),
        }
        labels = {
            'libelle': 'Libellé',
            'icone': 'Icône (ex: stethoscope)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = self.INPUT_CLASSES
        self.fields['description'].widget.attrs['class'] += ' resize-y'
