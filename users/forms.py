from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class LoginForm(forms.Form):
    username = forms.EmailField(label='Email', widget=forms.EmailInput)
    password = forms.CharField(label='Mot de passe', widget=forms.PasswordInput)


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=50, required=True)
    last_name = forms.CharField(max_length=50, required=True)
    telephone = forms.CharField(max_length=20, required=False)
    role = forms.ChoiceField(choices=User.Role.choices, initial=User.Role.PATIENT)

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'telephone', 'role', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'telephone', 'photo')
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'Prénom'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Nom'}),
            'telephone': forms.TextInput(attrs={'placeholder': '+224 6XX XXX XXX'}),
        }
