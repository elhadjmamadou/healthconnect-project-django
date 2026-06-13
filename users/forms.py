# ==============================================================================
# users/forms.py — Formulaires d'authentification et de profil utilisateur
# ==============================================================================
# Django sépare les formulaires des modèles et des vues pour respecter le
# principe de responsabilité unique (SRP). Ce fichier définit 3 formulaires :
#
# LoginForm    : saisie email + mot de passe pour la connexion
# RegisterForm : inscription avec création d'un nouvel utilisateur
# ProfileForm  : modification du profil (prénom, nom, téléphone, photo)
# ==============================================================================

from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class LoginForm(forms.Form):
    """
    Formulaire de connexion simple (email + mot de passe).

    Hérite de forms.Form (pas ModelForm) car on ne crée/modifie pas d'objet :
    on valide juste les données saisies avant d'appeler authenticate().

    Le champ s'appelle 'username' pour compatibilité avec AuthenticationForm
    de Django, mais l'utilisateur voit le label 'Email'.
    EmailInput : type="email" dans le HTML → validation native du navigateur.
    """
    username = forms.EmailField(label='Email', widget=forms.EmailInput)
    password = forms.CharField(label='Mot de passe', widget=forms.PasswordInput)


class RegisterForm(UserCreationForm):
    """
    Formulaire d'inscription d'un nouvel utilisateur.

    Hérite de UserCreationForm (Django built-in) qui gère :
      - Le champ password1 (mot de passe)
      - Le champ password2 (confirmation)
      - La vérification que les deux mots de passe sont identiques
      - Le hashage sécurisé du mot de passe avant sauvegarde

    On ajoute les champs propres à HealthConnect (prénom, nom, téléphone, rôle).

    Méthode save() surchargée pour deux raisons :
      1. Django AbstractUser exige un 'username' unique → on le remplit avec l'email
         (notre USERNAME_FIELD = 'email', mais le champ username reste en BDD)
      2. Le rôle est choisi à l'inscription (patient par défaut dans l'interface)
    """
    first_name = forms.CharField(max_length=50, required=True)
    last_name  = forms.CharField(max_length=50, required=True)
    telephone  = forms.CharField(max_length=20, required=False)
    # Le rôle peut être choisi à l'inscription (utile pour les tests/démo)
    role = forms.ChoiceField(choices=User.Role.choices, initial=User.Role.PATIENT)

    class Meta:
        model  = User
        fields = ('first_name', 'last_name', 'email', 'telephone', 'role', 'password1', 'password2')

    def save(self, commit=True):
        """
        Sauvegarde l'utilisateur en synchronisant username = email.

        AbstractUser hérite de AbstractBaseUser qui exige un USERNAME_FIELD unique.
        On utilise l'email comme USERNAME_FIELD, mais Django garde le champ
        'username' en base de données → on le remplit avec l'email pour éviter
        les erreurs de contrainte UNIQUE.
        """
        user = super().save(commit=False)
        user.username = user.email  # username = email pour éviter les doublons
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    """
    Formulaire de modification du profil utilisateur.

    ModelForm : lié au modèle User, génère automatiquement les champs
    et gère la sauvegarde (UPDATE SQL).

    Note : le mot de passe n'est PAS dans ce formulaire — il est géré
    séparément dans PasswordChangeView (users/views.py) pour des raisons
    de sécurité (confirmation de l'ancien mot de passe requise).

    request.FILES est nécessaire pour l'upload de la photo (ImageField).
    """
    class Meta:
        model  = User
        fields = ('first_name', 'last_name', 'telephone', 'photo')
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'Prénom'}),
            'last_name':  forms.TextInput(attrs={'placeholder': 'Nom'}),
            'telephone':  forms.TextInput(attrs={'placeholder': '+224 6XX XXX XXX'}),
        }
