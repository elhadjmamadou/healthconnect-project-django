from django.urls import path
from . import views

app_name = 'patients'

urlpatterns = [
    path('dashboard/', views.DashboardPatientView.as_view(), name='dashboard'),
    path('', views.ListePatientsView.as_view(), name='liste'),
    path('creer/', views.CreerPatientView.as_view(), name='creer'),
    path('<int:pk>/', views.DetailPatientView.as_view(), name='detail'),
    path('<int:pk>/modifier/', views.ModifierPatientView.as_view(), name='modifier'),
    path('<int:pk>/supprimer/', views.SupprimerPatientView.as_view(), name='supprimer'),
]
