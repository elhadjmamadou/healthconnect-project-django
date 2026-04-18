from django.urls import path
from . import views

app_name = 'rendez_vous'

urlpatterns = [
    path('', views.ListeRDVView.as_view(), name='liste'),
    path('reserver/', views.ReservationRDVView.as_view(), name='reserver'),
    path('<int:pk>/annuler/', views.AnnulerRDVView.as_view(), name='annuler'),
]
