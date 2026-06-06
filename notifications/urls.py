from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('tout-lire/', views.MarquerToutLuView.as_view(), name='tout_lire'),
    path('<int:pk>/lire/', views.MarquerLuView.as_view(), name='marquer_lu'),
    path('', views.ListeNotificationsView.as_view(), name='liste'),
    path('<int:pk>/lire/', views.MarquerLuView.as_view(), name='marquer_lu'),
    path('<int:pk>/supprimer/', views.SupprimerNotificationView.as_view(), name='supprimer'),
    path('tout-lire/', views.MarquerToutLuView.as_view(), name='tout_lire'),
]
