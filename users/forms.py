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
