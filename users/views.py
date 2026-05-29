from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import CreateView

from .forms import LoginForm, ProfileForm, RegisterForm
from .models import User


class LoginView(View):
    template_name = 'users/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('users:dashboard_redirect')
        return render(request, self.template_name, {'form': LoginForm()})

    def post(self, request):
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                next_url = request.GET.get('next', '')
                if next_url:
                    return redirect(next_url)
                return redirect('users:dashboard_redirect')
            else:
                form.add_error(None, 'Email ou mot de passe incorrect.')
        return render(request, self.template_name, {'form': form})


class RegisterView(View):
    template_name = 'users/register.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('users:dashboard_redirect')
        return render(request, self.template_name, {'form': RegisterForm()})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Bienvenue sur HealthConnect, {user.first_name} !')
            return redirect('users:dashboard_redirect')
        return render(request, self.template_name, {'form': form})


class LogoutView(View):
    def post(self, request):
        logout(request)
        return redirect('users:login')


@method_decorator(login_required, name='dispatch')
class DashboardRedirectView(View):
    def get(self, request):
        user = request.user
        if user.is_admin_role or user.is_staff:
            return redirect('rapports:dashboard_admin')
        elif user.is_medecin:
            return redirect('medecins:dashboard')
        else:
            return redirect('patients:dashboard')


@method_decorator(login_required, name='dispatch')
class ProfileView(View):
    template_name = 'users/profile.html'

    def get(self, request):
        form = ProfileForm(instance=request.user)
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil mis à jour avec succès.')
            return redirect('users:profile')
        return render(request, self.template_name, {'form': form})


@method_decorator(login_required, name='dispatch')
class PasswordChangeView(View):
    template_name = 'users/password_change.html'

    def get(self, request):
        form = PasswordChangeForm(request.user)
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Mot de passe modifié avec succès.')
            return redirect('users:profile')
        return render(request, self.template_name, {'form': form})
