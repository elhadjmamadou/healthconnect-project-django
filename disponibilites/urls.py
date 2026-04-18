from django.urls import path
from . import views

app_name = 'disponibilites'

urlpatterns = [
    path('', views.ListeDisponibilitesView.as_view(), name='liste'),
]
