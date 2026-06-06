from django import forms
from django.contrib.auth.forms import UserCreationForm

from users.models import User
from .models import Patient


class CreerPatientUserForm(UserCreationForm):
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
        user.role = User.Role.PATIENT
        if commit:
            user.save()
        return user


class PatientProfileForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = ('date_naissance', 'sexe', 'groupe_sanguin', 'adresse', 'allergies', 'antecedents_resumes')
        widgets = {
            'date_naissance': forms.DateInput(attrs={'type': 'date'}),
            'adresse': forms.Textarea(attrs={'rows': 3}),
            'allergies': forms.Textarea(attrs={'rows': 3}),
            'antecedents_resumes': forms.Textarea(attrs={'rows': 3}),
        }


class ModifierPatientUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'telephone', 'statut')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email
        if commit:
            user.save()
        return user
