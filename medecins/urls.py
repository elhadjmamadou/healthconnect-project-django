from django.urls import path
from . import views

app_name = 'medecins'

urlpatterns = [
    path('dashboard/', views.DashboardMedecinView.as_view(), name='dashboard'),
    path('', views.ListeMedecinsView.as_view(), name='liste'),
    path('creer/', views.CreerMedecinView.as_view(), name='creer'),
    path('specialites/', views.ListeSpecialitesView.as_view(), name='specialites'),
    path('specialites/creer/', views.CreerSpecialiteView.as_view(), name='creer_specialite'),
    path('specialites/<int:pk>/supprimer/', views.SupprimerSpecialiteView.as_view(), name='supprimer_specialite'),
    path('<int:pk>/', views.DetailMedecinView.as_view(), name='detail'),
    path('<int:pk>/modifier/', views.ModifierMedecinView.as_view(), name='modifier'),
    path('<int:pk>/supprimer/', views.SupprimerMedecinView.as_view(), name='supprimer'),
]
