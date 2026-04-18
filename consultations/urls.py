from django.urls import path
from . import views

app_name = 'consultations'

urlpatterns = [
    path('', views.ListeConsultationsView.as_view(), name='liste'),
    path('dossier/<int:pk>/', views.DossierMedicalView.as_view(), name='dossier'),
]
