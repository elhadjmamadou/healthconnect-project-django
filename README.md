# HealthConnect

Un système de gestion intégré pour les consultations médicales permettant une meilleure coordination entre patients, médecins et administrateurs. HealthConnect facilite la prise de rendez-vous, la gestion des consultations, le suivi des paiements et la gestion des dossiers médicaux.

## Table des matières

- [Fonctionnalités](#fonctionnalités)
- [Architecture](#architecture)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Configuration](#configuration)
- [Utilisation](#utilisation)
- [Structure du projet](#structure-du-projet)
- [API REST](#api-rest)

## Fonctionnalités

### Gestion des Utilisateurs
- Authentification par email avec rôles (Patient, Médecin, Administrateur)
- Gestion des profils utilisateur (photo, téléphone, statut)
- Système de statuts (Actif, Inactif, Suspendu)
- Traçabilité des modifications (date création/modification)

### Gestion des Patients
- Profil patient détaillé (date de naissance, sexe, groupe sanguin)
- Historique médical (allergies, antécédents)
- Calcul automatique de l'âge
- Adresse et coordonnées

### Gestion des Médecins
- Profils de médecins avec numéro d'ordre
- Spécialités multiples (Cardiologie, Dentaire, etc.)
- Tarification des consultations
- Modes d'exercice (Libéral, Salarié, Mixte)
- Gestion des nouveaux patients

### Rendez-vous et Consultations
- Prise de rendez-vous en ligne
- Gestion des disponibilités des médecins
- Historique des consultations
- Dossier médical avec rapports de consultation

### Paiements
- Intégration avec système de paiement (Djomy)
- Gestion des transactions
- Suivi des restants dus

### Notifications
- Système de notifications pour patients et médecins
- Rappels de rendez-vous

### Rapports Médicaux
- Génération et stockage de rapports
- Gestion des documents médicaux en PDF

## Architecture

### Stack Technologique
- **Backend** : Django 5.0+
- **Base de données** : PostgreSQL (via psycopg2)
- **API** : Django REST Framework
- **Frontend** : Bootstrap 5 avec Django Crispy Forms
- **Média** : Pillow pour traitement d'images
- **Serveur** : WhiteNoise pour fichiers statiques

### Structure des Applications Django

```
healthconnect/
├── users/              # Gestion des utilisateurs
├── patients/           # Profils patients
├── medecins/          # Profils médecins et spécialités
├── rendez_vous/       # Gestion des rendez-vous
├── consultations/     # Historique et dossier médical
├── disponibilites/    # Disponibilités médecins
├── paiements/         # Gestion des transactions
├── notifications/     # Système de notifications
├── rapports/          # Génération de rapports
├── config/            # Configuration Django
└── templates/         # Templates HTML
```

## Prérequis

- Python 3.10+
- PostgreSQL 12+
- pip / Virtual Environment
- Git

## Installation

### 1. Cloner le repository
```bash
git clone <repository-url>
cd healthconnect
```

### 2. Créer et activer l'environnement virtuel
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 3. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 4. Configuration des variables d'environnement
```bash
cp .env.example .env
# Éditer .env avec vos paramètres :
# - SECRET_KEY
# - DATABASE_URL
# - DEBUG
# - ALLOWED_HOSTS
```

### 5. Migrations de base de données
```bash
python manage.py migrate
```

### 6. Créer un superutilisateur
```bash
python manage.py createsuperuser
```

### 7. Collecter les fichiers statiques
```bash
python manage.py collectstatic --noinput
```

## Configuration

### Paramètres importants (config/settings/base.py)

- **LANGUAGE_CODE** : `fr-fr` (Français)
- **TIME_ZONE** : `Africa/Conakry`
- **AUTH_USER_MODEL** : Modèle User personnalisé
- **INSTALLED_APPS** : 9 applications métier + Django natif

### Dépendances principales (requirements.txt)

```
django>=5.0                          # Framework web
psycopg2-binary                      # Driver PostgreSQL
django-environ                       # Gestion variables ENV
djangorestframework                  # API REST
Pillow                              # Traitement d'images
django-crispy-forms                 # Formulaires Bootstrap
crispy-bootstrap5                    # Intégration Bootstrap 5
whitenoise                           # Fichiers statiques
requests                             # Requêtes HTTP
```

## Utilisation

### Démarrer le serveur de développement
```bash
python manage.py runserver
```

Le serveur sera accessible sur `http://localhost:8000`

### Panel d'administration
```
http://localhost:8000/admin
```
Connectez-vous avec les identifiants du superutilisateur créé.

### Rôles et permissions

- **Patient** : Peut prendre des rendez-vous, consulter son dossier médical
- **Médecin** : Peut gérer son planning, voir ses consultations, rédiger des rapports
- **Administrateur** : Accès complet au système, gestion des utilisateurs et configurations

## Structure du projet

### Applications incluses

#### users
- Modèle User personnalisé avec rôles
- Gestion d'authentification
- Profils utilisateur

#### patients
- Profil complet du patient
- Informations médicales (groupe sanguin, allergies)
- Antécédents médicaux

#### medecins
- Profil médecin avec numéro d'ordre
- Gestion des spécialités
- Configuration tarifs et mode d'exercice

#### rendez_vous
- Prise de rendez-vous
- Gestion d'agenda
- Signaux pour notifications

#### consultations
- Historique des consultations
- Dossier médical du patient
- Signaux pour notifications

#### disponibilites
- Créneau de disponibilité
- Planning médecin

#### paiements
- Intégration Djomy (paiement)
- Gestion des transactions

#### notifications
- Notifications de rendez-vous
- Historique de communications

#### rapports
- Génération de rapports PDF
- Stockage en base de données

### Structure des fichiers statiques et médias

```
static/
├── css/
│   └── custom.css
├── images/
└── js/
    └── main.js

media/
├── users/photos/
└── rapports/generated/
```

## API REST

L'API REST est disponible via Django REST Framework. Les bases sont en place avec les modèles définis.

### Points d'accès disponibles (à configurer selon besoin)
- `/api/patients/`
- `/api/medecins/`
- `/api/rendez_vous/`
- `/api/consultations/`
- `/api/paiements/`

## Localisation

- **Langue** : Français
- **Fuseau horaire** : Afrique/Conakry (GMT+0)

## Informations supplémentaires

### Bases de données
- SQLite pour développement (configuration par défaut)
- PostgreSQL pour production (configurable via environ)

### Sécurité
- Middleware de sécurité Django activé
- Protection CSRF activée
- Validation des mots de passe personnalisée

## Auteur

HealthConnect - Système de gestion médical intégré

---

**Dernière mise à jour** : 11 mai 2026
