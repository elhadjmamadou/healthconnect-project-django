from django.urls import path
from . import views

app_name = 'patients'

urlpatterns = [
    path('dashboard/', views.DashboardPatientView.as_view(), name='dashboard'),
    path('', views.ListePatientsView.as_view(), name='liste'),
    path('<int:pk>/', views.DetailPatientView.as_view(), name='detail'),
]
