# ==============================================================================
# medecins/forms.py — Formulaires de gestion des médecins et spécialités
# ==============================================================================
# Ce fichier contient 4 formulaires utilisés par les vues admin des médecins :
#
# CreerMedecinUserForm    : création du compte User pour un nouveau médecin
# MedecinProfileForm      : profil professionnel (numéro d'ordre, tarif, spécialités)
# ModifierMedecinUserForm : modification des données du compte User existant
# SpecialiteForm          : ajout/modification d'une spécialité médicale
# ==============================================================================

from django import forms
from django.contrib.auth.forms import UserCreationForm

from users.models import User
from .models import Medecin, Specialite


class CreerMedecinUserForm(UserCreationForm):
    """
    Formulaire de création du compte User pour un médecin (admin seulement).

    Hérite de UserCreationForm pour bénéficier de :
      - password1 / password2 avec vérification de correspondance
      - Hashage automatique du mot de passe avant sauvegarde

    La méthode save() est surchargée pour :
      1. Forcer username = email (contrainte AbstractUser)
      2. Forcer role = MEDECIN (un compte créé ici est TOUJOURS médecin)
    """

    class Meta:
        model  = User
        fields = ('first_name', 'last_name', 'email', 'telephone')
        labels = {
            'first_name': 'Prénom',
            'last_name':  'Nom',
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email        # synchronisation obligatoire (AbstractUser)
        user.role     = User.Role.MEDECIN # tous les comptes créés ici sont des médecins
        if commit:
            user.save()
        return user


class MedecinProfileForm(forms.ModelForm):
    """
    Formulaire du profil professionnel d'un médecin.

    Champ spécialités : ModelMultipleChoiceField avec CheckboxSelectMultiple
    → affiché comme des cases à cocher (un médecin peut avoir plusieurs spécialités).
    Le champ est optionnel (required=False) car un médecin peut n'en avoir aucune.

    save_m2m() : après un commit=False + save(), il faut appeler manuellement
    save_m2m() pour sauvegarder les relations ManyToMany (spécialités).
    C'est fait dans CreerMedecinView.post() et ModifierMedecinView.post().
    """

    specialites = forms.ModelMultipleChoiceField(
        queryset=Specialite.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Spécialités',
    )

    class Meta:
        model  = Medecin
        fields = ('numero_ordre', 'biographie', 'tarif_consultation',
                  'mode_exercice', 'specialites', 'accepte_nouveaux_patients')
        widgets = {
            'biographie': forms.Textarea(attrs={'rows': 4}),
        }


class ModifierMedecinUserForm(forms.ModelForm):
    """
    Formulaire de modification des données du compte User d'un médecin.

    Différence avec CreerMedecinUserForm :
      - Pas de champs password1/password2 (le mot de passe est géré séparément)
      - Ajout du champ 'statut' (activer/désactiver/suspendre le compte)
      - Instance=medecin.user → UPDATE SQL sur l'utilisateur existant

    save() resynchronise username=email au cas où l'email a été modifié.
    """

    class Meta:
        model  = User
        fields = ('first_name', 'last_name', 'email', 'telephone', 'statut')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email  # si l'email a changé, on met à jour le username aussi
        if commit:
            user.save()
        return user


class SpecialiteForm(forms.ModelForm):
    """
    Formulaire d'ajout/modification d'une spécialité médicale.

    INPUT_CLASSES : classes Tailwind CSS appliquées à tous les champs via __init__.
    Cette approche centralisée (une seule constante) garantit un style uniforme
    sur tous les champs sans répéter les classes dans chaque widget.

    __init__ : appelée à chaque instanciation du formulaire.
    On itère sur self.fields.values() pour ajouter la classe CSS à chaque widget.
    Le champ 'description' (Textarea) reçoit en plus 'resize-y' pour permettre
    à l'utilisateur de redimensionner verticalement la zone de texte.
    """

    # Classes Tailwind communes à tous les champs du formulaire
    INPUT_CLASSES = (
        'w-full bg-background border border-outline-variant/50 rounded-xl '
        'px-4 py-3 text-sm text-on-surface placeholder:text-on-surface-variant/40'
    )

    class Meta:
        model  = Specialite
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
            'icone':   'Icône (ex: stethoscope)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Application des classes CSS à TOUS les champs en une seule boucle
        for field in self.fields.values():
            field.widget.attrs['class'] = self.INPUT_CLASSES
        # La textarea description peut être redimensionnée verticalement
        self.fields['description'].widget.attrs['class'] += ' resize-y'
