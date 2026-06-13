# ==============================================================================
# patients/forms.py — Formulaires de gestion des comptes patients
# ==============================================================================
# Ce fichier contient 3 formulaires utilisés par les vues admin des patients :
#
# CreerPatientUserForm   : création du compte User pour un nouveau patient
#                          Hérite de UserCreationForm → password1/password2 + hashage
# PatientProfileForm     : profil médical (date naissance, sexe, groupe sanguin…)
# ModifierPatientUserForm: modification du User existant (sans champ mot de passe)
#
# Même structure que medecins/forms.py : un formulaire pour le User (auth)
# et un formulaire pour le profil métier (Patient).
# La séparation est nécessaire car User et Patient sont deux modèles distincts.
# ==============================================================================

from django import forms
from django.contrib.auth.forms import UserCreationForm

from users.models import User
from .models import Patient


class CreerPatientUserForm(UserCreationForm):
    """
    Formulaire de création du compte User pour un patient (admin seulement).

    Hérite de UserCreationForm (Django built-in) qui fournit :
      - password1 (saisie du mot de passe)
      - password2 (confirmation)
      - Validation que password1 == password2
      - Hashage automatique (PBKDF2+SHA256) avant sauvegarde

    save() est surchargé pour :
      1. username = email  : AbstractUser exige un username unique.
                             On utilise l'email comme username pour éviter un doublon.
      2. role = PATIENT    : tous les comptes créés via ce formulaire sont des patients.
                             Impossible pour un admin de créer un médecin via ce formulaire.
    """

    class Meta:
        model  = User
        fields = ('first_name', 'last_name', 'email', 'telephone')
        labels = {
            'first_name': 'Prénom',
            'last_name':  'Nom',
        }

    def save(self, commit=True):
        user          = super().save(commit=False)  # crée l'objet sans INSERT encore
        user.username = user.email                  # synchronisation username ↔ email (obligatoire)
        user.role     = User.Role.PATIENT           # force le rôle patient (non modifiable par l'admin)
        if commit:
            user.save()  # INSERT SQL avec mot de passe haché
        return user


class PatientProfileForm(forms.ModelForm):
    """
    Formulaire du profil médical d'un patient.

    Widgets HTML5 :
      type="date" → sélecteur de date natif (pas besoin de jQuery UI datepicker)
      rows=3      → textarea de taille réduite pour adresse, allergies, antécédents

    Champs :
      date_naissance       : pour le calcul de l'âge (Patient.age property)
      sexe                 : M/F, affiché comme <select>
      groupe_sanguin       : A+, A-, B+, B-, AB+, AB-, O+, O-
      adresse              : domicile du patient
      allergies            : liste des allergies connues (texte libre)
      antecedents_resumes  : résumé des antécédents médicaux importants
    """

    class Meta:
        model  = Patient
        fields = ('date_naissance', 'sexe', 'groupe_sanguin', 'adresse',
                  'allergies', 'antecedents_resumes')
        widgets = {
            'date_naissance':      forms.DateInput(attrs={'type': 'date'}),   # sélecteur natif
            'adresse':             forms.Textarea(attrs={'rows': 3}),
            'allergies':           forms.Textarea(attrs={'rows': 3}),
            'antecedents_resumes': forms.Textarea(attrs={'rows': 3}),
        }


class ModifierPatientUserForm(forms.ModelForm):
    """
    Formulaire de modification du compte User d'un patient existant.

    Différences avec CreerPatientUserForm :
      - Pas de password1/password2 (le mot de passe est géré séparément)
      - Ajout du champ 'statut' (actif / inactif / suspendu)
      - Hérite de ModelForm (pas UserCreationForm) → UPDATE, pas INSERT

    save() resynchronise username=email :
      Si l'admin change l'email du patient, le username doit aussi être mis à jour.
      AbstractUser exige username unique → sans cette synchro, l'ancien username
      resterait en base avec l'ancien email, ce qui créerait une incohérence.
    """

    class Meta:
        model  = User
        fields = ('first_name', 'last_name', 'email', 'telephone', 'statut')

    def save(self, commit=True):
        user          = super().save(commit=False)
        user.username = user.email  # si email modifié → username mis à jour aussi
        if commit:
            user.save()
        return user
