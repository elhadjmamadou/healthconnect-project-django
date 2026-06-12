"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

from users.views import LandingView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("users/", include("users.urls", namespace="users")),
    path("patients/", include("patients.urls", namespace="patients")),
    path("medecins/", include("medecins.urls", namespace="medecins")),
    path("rendez-vous/", include("rendez_vous.urls", namespace="rendez_vous")),
    path("consultations/", include("consultations.urls", namespace="consultations")),
    path("disponibilites/", include("disponibilites.urls", namespace="disponibilites")),
    path("paiements/", include("paiements.urls", namespace="paiements")),
    path("notifications/", include("notifications.urls", namespace="notifications")),
    path("rapports/", include("rapports.urls", namespace="rapports")),
    path("", LandingView.as_view(), name="home"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
