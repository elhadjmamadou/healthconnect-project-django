from django.urls import path
from . import views

app_name = 'disponibilites'

urlpatterns = [
    path('', views.ListeDisponibilitesView.as_view(), name='liste'),
    path('<int:pk>/modifier/', views.ModifierDisponibiliteView.as_view(), name='modifier'),
    path('<int:pk>/supprimer/', views.SupprimerDisponibiliteView.as_view(), name='supprimer'),
]
