# ==============================================================================
# consultations/urls.py — Routes de l'application consultations
# ==============================================================================
# app_name = 'consultations' : espace de noms pour les URLs.
# Permet d'écrire {% url 'consultations:detail' pk=1 %} dans les templates
# sans conflit si une autre app a aussi une vue nommée 'detail'.
#
# Routes spéciales :
#   ordonnance/verifier/<uuid:token>/ — page PUBLIQUE (sans login)
#     Le token est un UUID v4 encodé dans le QR code de l'ordonnance PDF.
#     <uuid:token> : convertisseur Django qui valide le format UUID avant
#     d'appeler la vue (évite les erreurs si quelqu'un passe une chaîne aléatoire).
#
#   ordonnance/<int:pk>/pdf/ — génère le PDF à la volée via WeasyPrint
#
# Ordre des routes : Django teste les patterns dans l'ordre et s'arrête
# au premier match. Les routes avec des préfixes fixes (ex: 'dossiers/')
# doivent être avant les routes dynamiques (ex: '<int:pk>/').
# ==============================================================================

from django.urls import path
from . import views

app_name = 'consultations'

urlpatterns = [
    # Liste de toutes les consultations (admin)
    path('', views.ListeConsultationsView.as_view(), name='liste'),

    # Gestion des dossiers médicaux
    path('dossiers/', views.ListeDossiersView.as_view(), name='liste_dossiers'),
    path('mon-dossier/', views.MonDossierView.as_view(), name='mon_dossier'),
    path('dossier/<int:pk>/', views.DossierMedicalView.as_view(), name='dossier'),

    # CRUD des consultations
    path('creer/<int:rdv_pk>/', views.CreerConsultationView.as_view(), name='creer'),
    path('<int:pk>/editer/', views.EditerConsultationView.as_view(), name='editer'),
    path('<int:pk>/supprimer/', views.SupprimerConsultationView.as_view(), name='supprimer'),

    # Ordonnance numérique (médecin connecté)
    path('<int:pk>/ordonnance/', views.RedigerOrdonnanceView.as_view(), name='rediger_ordonnance'),
    path('ordonnance/<int:pk>/pdf/', views.OrdonnancePDFView.as_view(), name='ordonnance_pdf'),

    # Vérification publique via QR code (aucune connexion requise)
    # <uuid:token> : valide le format UUID automatiquement
    path('ordonnance/verifier/<uuid:token>/', views.VerifierOrdonnanceView.as_view(), name='verifier_ordonnance'),

    # Détail (placé en dernier pour éviter de masquer les routes préfixées)
    path('<int:pk>/', views.DetailConsultationView.as_view(), name='detail'),
]
