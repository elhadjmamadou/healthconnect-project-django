from django.urls import path
from . import views

app_name = 'medecins'

urlpatterns = [
    path('dashboard/', views.DashboardMedecinView.as_view(), name='dashboard'),
    path('', views.ListeMedecinsView.as_view(), name='liste'),
    path('<int:pk>/', views.DetailMedecinView.as_view(), name='detail'),
]
