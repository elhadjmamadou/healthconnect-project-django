from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import CreateView

from .forms import LoginForm, RegisterForm
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
