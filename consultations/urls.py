from django.urls import path
from . import views

app_name = 'consultations'

urlpatterns = [
    path('', views.ListeConsultationsView.as_view(), name='liste'),
    path('dossiers/', views.ListeDossiersView.as_view(), name='liste_dossiers'),
    path('mon-dossier/', views.MonDossierView.as_view(), name='mon_dossier'),
    path('dossier/<int:pk>/', views.DossierMedicalView.as_view(), name='dossier'),
    path('creer/<int:rdv_pk>/', views.CreerConsultationView.as_view(), name='creer'),
    path('<int:pk>/editer/', views.EditerConsultationView.as_view(), name='editer'),
    path('<int:pk>/supprimer/', views.SupprimerConsultationView.as_view(), name='supprimer'),
    path('<int:pk>/', views.DetailConsultationView.as_view(), name='detail'),
]
