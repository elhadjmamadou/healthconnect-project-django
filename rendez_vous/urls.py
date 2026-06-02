from django.urls import path
from . import views

app_name = 'rendez_vous'

urlpatterns = [
    path('', views.ListeRDVView.as_view(), name='liste'),
    path('reserver/', views.ReservationRDVView.as_view(), name='reserver'),
    path('<int:pk>/', views.DetailRDVView.as_view(), name='detail'),
    path('<int:pk>/confirmer/', views.ConfirmerRDVView.as_view(), name='confirmer'),
    path('<int:pk>/refuser/', views.RefuserRDVView.as_view(), name='refuser'),
    path('<int:pk>/annuler/', views.AnnulerRDVView.as_view(), name='annuler'),
]
