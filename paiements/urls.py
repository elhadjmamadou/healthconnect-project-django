from django.urls import path
from . import views

app_name = 'paiements'

urlpatterns = [
    path('', views.ListePaiementsView.as_view(), name='liste'),
    path('<int:pk>/', views.DetailPaiementView.as_view(), name='detail'),
    path('webhook/djomy/', views.WebhookDjomyView.as_view(), name='webhook_djomy'),
]
