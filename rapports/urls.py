from django.urls import path
from . import views

app_name = 'rapports'

urlpatterns = [
    path('dashboard/', views.DashboardAdminView.as_view(), name='dashboard_admin'),
    path('analytiques/', views.AnalytiquesView.as_view(), name='analytiques'),
]
