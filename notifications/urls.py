from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.ListeNotificationsView.as_view(), name='liste'),
]
