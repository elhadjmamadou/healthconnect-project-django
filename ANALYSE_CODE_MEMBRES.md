# Analyse du code des membres HealthConnect

Date d'analyse : 09/06/2026

## 1. Périmètre analysé

Dans ce projet, le mot "membre" correspond principalement aux comptes et profils utilisateurs de HealthConnect :

- `users` : compte principal, authentification, rôles, profil commun, mot de passe.
- `patients` : profil métier d'un utilisateur patient.
- `medecins` : profil métier d'un utilisateur médecin et spécialités.
- Templates associés : `templates/users`, `templates/patients`, `templates/medecins`, plus `navbar` et `sidebar`.
- Dépendances directes : rendez-vous, disponibilités, consultations, paiements, notifications, rapports et commande de seed.

L'architecture est basée sur un compte unique `users.User`, puis sur un profil spécialisé selon le rôle :

```text
User
├── role = patient  -> Patient
├── role = medecin  -> Medecin
└── role = admin    -> accès administration applicative
```

## 2. Architecture générale

### 2.1 Compte principal

Le modèle central est `users.models.User`. Il hérite de `django.contrib.auth.models.AbstractUser`, donc il garde les champs Django classiques : `username`, `password`, `first_name`, `last_name`, `is_staff`, `is_superuser`, groupes et permissions.

Le projet ajoute :

- `email` unique, utilisé comme identifiant de connexion.
- `role` avec trois valeurs : `patient`, `medecin`, `admin`.
- `telephone`.
- `photo`.
- `statut` : `actif`, `inactif`, `suspendu`.
- `date_creation` et `date_modification`.

La ligne importante est :

```python
USERNAME_FIELD = 'email'
```

Cela veut dire que l'utilisateur se connecte avec son email, même si le champ `username` existe encore pour compatibilité Django.

### 2.2 Profils métier

Le profil patient est dans `patients.models.Patient`.

Relation :

```python
user = models.OneToOneField('users.User', related_name='patient_profile')
```

Donc un utilisateur patient ne peut avoir qu'un seul profil patient.

Le profil médecin est dans `medecins.models.Medecin`.

Relation :

```python
user = models.OneToOneField('users.User', related_name='medecin_profile')
```

Donc un utilisateur médecin ne peut avoir qu'un seul profil médecin.

### 2.3 Création automatique des profils

Le fichier `users/signals.py` écoute la création d'un `User`.

Quand un `User` est créé :

- si `role == medecin`, le signal crée un `Medecin` avec un numéro d'ordre automatique ;
- si `role == patient`, le signal crée un `Patient`.

Ce mécanisme est activé dans `users/apps.py` :

```python
def ready(self):
    import users.signals
```

Cela charge les signaux au démarrage de Django.

## 3. Configuration Django liée aux membres

### `config/settings/base.py`

Points importants :

- `users`, `patients` et `medecins` sont dans `INSTALLED_APPS`.
- `AUTH_USER_MODEL = 'users.User'` indique à Django d'utiliser le modèle utilisateur personnalisé.
- `LOGIN_URL = '/users/login/'`.
- `LOGIN_REDIRECT_URL = '/dashboard/'`.
- `MEDIA_ROOT` et `MEDIA_URL` servent aux photos de profil.
- Le context processor `notifications.context_processors.notifications_non_lues` injecte le nombre de notifications non lues dans les templates.

### `config/urls.py`

Les routes globales branchent les modules :

- `/users/` -> authentification et profil.
- `/patients/` -> espace patient et CRUD patient.
- `/medecins/` -> espace médecin, liste, détail, spécialités et CRUD médecin.
- `/` redirige vers `users:login`.

## 4. Application `users`

### 4.1 `users/models.py`

Ce fichier définit le modèle `User`.

Classes internes :

- `Role` : contient `PATIENT`, `MEDECIN`, `ADMIN`.
- `Statut` : contient `ACTIF`, `INACTIF`, `SUSPENDU`.

Propriétés pratiques :

- `is_patient` retourne `True` si le rôle est `patient`.
- `is_medecin` retourne `True` si le rôle est `medecin`.
- `is_admin_role` retourne `True` si le rôle est `admin`.

Ces propriétés sont utilisées partout dans les vues et templates pour afficher le bon menu ou protéger certaines pages.

### 4.2 `users/forms.py`

Le fichier contient trois formulaires.

`LoginForm`

- Demande un email et un mot de passe.
- Le champ s'appelle `username` côté formulaire parce que Django attend souvent ce nom pour l'authentification.

`RegisterForm`

- Hérite de `UserCreationForm`.
- Demande prénom, nom, téléphone, rôle, mot de passe et confirmation.
- Dans `save()`, il copie l'email dans `username` :

```python
user.username = user.email
```

Cela évite d'avoir à demander un username séparé.

`ProfileForm`

- Permet à l'utilisateur connecté de modifier son prénom, nom, téléphone et photo.
- Ne permet pas de modifier l'email, le rôle ou le statut.

### 4.3 `users/views.py`

`LoginView`

- En `GET`, affiche le formulaire de connexion.
- Si l'utilisateur est déjà connecté, redirige vers `users:dashboard_redirect`.
- En `POST`, récupère email + mot de passe, appelle `authenticate()`, puis connecte avec `login()`.
- Si `next` existe dans l'URL, l'utilisateur est redirigé vers cette page.

`RegisterView`

- Affiche le formulaire d'inscription.
- Crée le `User`.
- Connecte immédiatement le nouvel utilisateur.
- Redirige vers le dashboard adapté au rôle.

`LogoutView`

- Déconnecte l'utilisateur uniquement en `POST`.
- Redirige vers la page de connexion.

`DashboardRedirectView`

- Redirection selon le rôle :
  - admin ou staff -> `rapports:dashboard_admin`
  - médecin -> `medecins:dashboard`
  - sinon -> `patients:dashboard`

`ProfileView`

- Page profil commune.
- En `GET`, affiche le formulaire avec les données de `request.user`.
- En `POST`, sauvegarde les changements.

`PasswordChangeView`

- Utilise `PasswordChangeForm` de Django.
- Appelle `update_session_auth_hash()` après changement du mot de passe pour éviter de déconnecter l'utilisateur.

### 4.4 `users/urls.py`

Routes principales :

- `/users/login/`
- `/users/register/`
- `/users/logout/`
- `/users/dashboard/`
- `/users/profile/`
- `/users/password-change/`
- `/users/password-reset/`
- `/users/password-reset/done/`
- `/users/password-reset/confirm/<uidb64>/<token>/`
- `/users/password-reset/complete/`

Le flow reset password utilise les vues Django intégrées.

### 4.5 `users/mixins.py`

Ce fichier centralise les protections par rôle.

`PatientRequiredMixin`

- Exige une session connectée.
- Autorise seulement `request.user.is_patient`.

`MedecinRequiredMixin`

- Exige une session connectée.
- Autorise seulement `request.user.is_medecin`.

`AdminRequiredMixin`

- Exige une session connectée.
- Autorise `request.user.is_admin_role` ou `request.user.is_staff`.

Ces mixins évitent de répéter les mêmes conditions dans toutes les vues.

### 4.6 `users/signals.py`

Fonction `create_role_profile`

- Déclenchée après `post_save` sur `User`.
- Ne fait rien si l'utilisateur n'est pas nouvellement créé.
- Crée automatiquement :
  - un `Medecin` si le rôle est médecin ;
  - un `Patient` si le rôle est patient.

Pour les médecins, le numéro d'ordre automatique ressemble à :

```text
ORD-XXXXXXXX
```

Le code utilise `get_or_create()`, ce qui évite de créer deux profils si le signal se déclenche plusieurs fois.

### 4.7 `users/admin.py`

Le modèle `User` est intégré à l'admin Django avec :

- affichage email, prénom, nom, rôle, statut, staff ;
- filtres par rôle/statut/staff/superuser ;
- recherche par email, prénom, nom, téléphone ;
- section supplémentaire "Profil HealthConnect".

### 4.8 Templates `templates/users`

`login.html`

- Page de connexion.
- Champ email, champ mot de passe, bouton afficher/masquer le mot de passe.
- Lien vers mot de passe oublié.
- Lien vers inscription.

`register.html`

- Page d'inscription.
- Interface avec choix patient/médecin.
- Champs identité, email, téléphone, mot de passe.
- JavaScript simple pour sélectionner visuellement le rôle et afficher/masquer le mot de passe.

`profile.html`

- Affiche l'identité du membre connecté.
- Affiche son rôle.
- Formulaire de modification des infos communes.
- Affiche aussi un bloc spécifique selon le rôle :
  - dossier patient si patient ;
  - profil médecin si médecin.

`password_change.html`

- Formulaire de changement de mot de passe connecté.

Templates `templates/registration`

- Pages du reset password Django : demande, confirmation, terminé.
- Attention : `users/urls.py` référence aussi `registration/password_reset_email.html` et `registration/password_reset_subject.txt`, mais ces fichiers ne sont pas présents dans le dépôt au moment de l'analyse.

## 5. Application `patients`

### 5.1 `patients/models.py`

Le modèle `Patient` complète `User` avec des informations médicales simples.

Champs :

- `user` : relation unique vers `users.User`.
- `date_naissance`.
- `sexe` : `M`, `F`, `autre`.
- `adresse`.
- `groupe_sanguin`.
- `allergies`.
- `antecedents_resumes`.
- dates de création et modification.

Propriétés :

`nom_complet`

- Retourne `user.get_full_name()`.
- Si le nom complet est vide, retourne l'email.

`age`

- Calcule l'âge à partir de `date_naissance`.
- Retourne `None` si la date de naissance n'est pas renseignée.

### 5.2 `patients/forms.py`

`CreerPatientUserForm`

- Crée le compte `User`.
- Force `role = User.Role.PATIENT`.
- Copie `email` dans `username`.

`PatientProfileForm`

- Modifie les données médicales du patient.
- Utilise des widgets adaptés : input date, textarea pour adresse/allergies/antécédents.

`ModifierPatientUserForm`

- Modifie les infos communes du compte : prénom, nom, email, téléphone, statut.
- Recopie l'email dans `username`.

### 5.3 `patients/views.py`

`DashboardPatientView`

- Protégée par `PatientRequiredMixin`.
- Récupère le profil patient avec `request.user.patient_profile`.
- Calcule :
  - prochain rendez-vous ;
  - nombre de rendez-vous sur l'année ;
  - nombre de consultations ;
  - cinq consultations récentes.

`ListePatientsView`

- Protégée seulement par `LoginRequiredMixin`.
- Liste les patients avec `select_related('user')`.
- Ajoute `nb_rdv` avec `Count('rendez_vous')`.
- Filtres disponibles :
  - recherche texte sur prénom, nom, email ;
  - sexe ;
  - statut utilisateur.

`DetailPatientView`

- Protégée seulement par `LoginRequiredMixin`.
- Affiche la fiche complète d'un patient.

`CreerPatientView`

- Protégée par `AdminRequiredMixin`.
- Affiche deux formulaires : compte utilisateur + profil patient.
- En `POST`, sauvegarde le `User`, puis le `Patient`.
- Utilise `transaction.atomic` pour que la création soit annulée en bloc en cas d'erreur.

`ModifierPatientView`

- Protégée par `AdminRequiredMixin`.
- Modifie le compte `User` et le profil `Patient`.

`SupprimerPatientView`

- Protégée par `AdminRequiredMixin`.
- Supprime `patient.user`.
- Comme `Patient.user` est en `on_delete=models.CASCADE`, le profil patient est supprimé avec le compte.

### 5.4 `patients/urls.py`

Routes :

- `/patients/dashboard/`
- `/patients/`
- `/patients/creer/`
- `/patients/<pk>/`
- `/patients/<pk>/modifier/`
- `/patients/<pk>/supprimer/`

### 5.5 `patients/admin.py`

Admin simple :

- affiche nom, sexe, date de naissance, groupe sanguin ;
- filtres sexe et groupe sanguin ;
- recherche par nom/prénom/email utilisateur ;
- champ `user` en raw id.

### 5.6 Templates `templates/patients`

`dashboard_patient.html`

- Espace patient.
- Affiche une salutation, le groupe sanguin, le prochain RDV, les statistiques, un accès à la prise de RDV et les consultations récentes.

`liste_patients.html`

- Tableau de patients.
- Recherche et filtres.
- Affiche patient, âge, groupe sanguin, nombre de RDV, statut.
- Le bouton "Ajouter un patient" apparaît seulement pour admin/staff.

`detail_patient.html`

- Dossier patient.
- Affiche identité, contact, statut, âge, groupe sanguin.
- Affiche informations médicales, allergies, antécédents.
- Affiche le dossier médical lié si présent.
- Affiche les rendez-vous récents.
- Les actions modifier/supprimer sont réservées admin/staff.

`creer_patient.html`

- Formulaire admin de création patient.
- Sépare informations du compte et profil médical.

`modifier_patient.html`

- Formulaire admin de modification patient.
- Sépare compte utilisateur et profil médical.

## 6. Application `medecins`

### 6.1 `medecins/models.py`

Deux modèles existent.

`Specialite`

- `libelle` unique.
- `description`.
- `icone`.
- dates création/modification.

`Medecin`

Champs :

- `user` : relation unique vers `users.User`.
- `numero_ordre` unique.
- `biographie`.
- `tarif_consultation`.
- `mode_exercice` : libéral, salarié, mixte.
- `specialites` : relation `ManyToMany` vers `Specialite`.
- `accepte_nouveaux_patients`.
- dates création/modification.

Propriétés :

- `nom_complet` : nom complet du `User` ou email.
- `specialites_list` : liste des libellés de spécialités.

### 6.2 `medecins/forms.py`

`CreerMedecinUserForm`

- Crée un `User`.
- Force `role = User.Role.MEDECIN`.
- Copie email vers username.

`MedecinProfileForm`

- Formulaire du profil médecin.
- Gère aussi les spécialités via `ModelMultipleChoiceField`.
- Widget checkbox pour sélectionner plusieurs spécialités.

`ModifierMedecinUserForm`

- Modifie prénom, nom, email, téléphone, statut.

`SpecialiteForm`

- Crée une spécialité.
- Champs : libellé, description, icône.

### 6.3 `medecins/views.py`

`DashboardMedecinView`

- Protégée par `MedecinRequiredMixin`.
- Récupère `request.user.medecin_profile`.
- Calcule :
  - rendez-vous du jour ;
  - nombre de RDV du jour ;
  - patients distincts du mois ;
  - consultations totales ;
  - prochains RDV ;
  - consultations récentes.

`ListeMedecinsView`

- Protégée par `LoginRequiredMixin`.
- Charge les médecins avec `select_related('user')` et `prefetch_related('specialites')`.
- Ajoute `nb_rdv`.
- Filtres :
  - recherche texte sur prénom, nom, numéro d'ordre, spécialité ;
  - spécialité ;
  - statut actif/inactif.

`DetailMedecinView`

- Protégée par `LoginRequiredMixin`.
- Affiche le profil d'un médecin.

`CreerMedecinView`

- Protégée par `AdminRequiredMixin`.
- Crée le compte utilisateur + profil médecin.
- Sauvegarde les relations many-to-many avec `profile_form.save_m2m()`.

`ModifierMedecinView`

- Protégée par `AdminRequiredMixin`.
- Modifie le compte et le profil médecin.

`SupprimerMedecinView`

- Protégée par `AdminRequiredMixin`.
- Supprime le `User`, ce qui supprime le `Medecin` par cascade.

`ListeSpecialitesView`

- Protégée par `AdminRequiredMixin`.
- Liste les spécialités.
- Annote chaque spécialité avec `nb_medecins`.
- Ajoute le formulaire de création dans le contexte.

`CreerSpecialiteView`

- Crée une spécialité en `POST`.
- Envoie les erreurs Django dans les messages si le formulaire est invalide.

`SupprimerSpecialiteView`

- Supprime une spécialité.

### 6.4 `medecins/urls.py`

Routes :

- `/medecins/dashboard/`
- `/medecins/`
- `/medecins/creer/`
- `/medecins/specialites/`
- `/medecins/specialites/creer/`
- `/medecins/specialites/<pk>/supprimer/`
- `/medecins/<pk>/`
- `/medecins/<pk>/modifier/`
- `/medecins/<pk>/supprimer/`

### 6.5 `medecins/admin.py`

Admin :

- `SpecialiteAdmin` affiche libellé et icône.
- `MedecinAdmin` affiche nom, numéro d'ordre, mode, tarif et acceptation de nouveaux patients.
- Filtres par mode, acceptation, spécialités.
- `filter_horizontal` pour gérer facilement les spécialités.

### 6.6 Templates `templates/medecins`

`dashboard_medecin.html`

- Tableau de bord médecin.
- Affiche agenda du jour, prochains RDV, consultations récentes.
- Ajoute des boutons pour créer une consultation depuis un RDV actif.

`liste_medecins.html`

- Liste sous forme de cartes.
- Filtres par recherche, spécialité, statut.
- Affiche photo/initiales, spécialités, tarif, mode d'exercice, statut.
- Certaines actions de modification utilisent actuellement des liens directs vers `/admin/...`.

`detail_medecin.html`

- Profil public/interne du médecin.
- Affiche identité, contact, numéro d'ordre, statut, spécialités, tarif, biographie.
- Affiche les prochaines disponibilités libres.
- Affiche les rendez-vous récents pour admin ou médecin.

`creer_medecin.html`

- Formulaire admin de création médecin.
- Sépare compte utilisateur et profil médecin.
- Gère les spécialités via cases à cocher.

`modifier_medecin.html`

- Formulaire admin de modification médecin.

`specialites.html`

- Page admin de gestion des spécialités.
- Formulaire d'ajout à gauche.
- Liste des spécialités à droite avec compteur de médecins.

## 7. Composants communs

### `templates/components/sidebar.html`

La sidebar affiche un menu différent selon le rôle.

Admin :

- dashboard admin ;
- médecins ;
- spécialités ;
- patients ;
- rendez-vous ;
- dossiers médicaux ;
- paiements ;
- rapports.

Médecin :

- dashboard médecin ;
- agenda ;
- patients ;
- consultations ;
- disponibilités ;
- notifications.

Patient :

- dashboard patient ;
- prise de RDV ;
- rendez-vous ;
- dossier médical ;
- paiements ;
- notifications.

En bas :

- paramètres ;
- lien profil ;
- bouton déconnexion.

### `templates/components/navbar.html`

La navbar affiche :

- bouton menu mobile ;
- titre de page ;
- icône notifications avec badge ;
- avatar ou initiales ;
- nom et rôle du membre connecté.

## 8. Dépendances avec les autres modules

### Consultations

`consultations.models.DossierMedical`

- Relié à `Patient` en `OneToOneField`.
- Un patient a donc un seul dossier médical.
- Le numéro de dossier est généré automatiquement si absent.

`consultations.signals.creer_dossier_medical`

- Crée automatiquement un `DossierMedical` quand un `Patient` est créé.

`consultations.models.Consultation`

- Reliée à un dossier médical.
- Reliée à un médecin.
- Peut être reliée à un rendez-vous.

`consultations.signals.marquer_rdv_termine`

- Quand une consultation est créée avec un rendez-vous, le rendez-vous passe à `termine`.

### Rendez-vous

`rendez_vous.models.RendezVous`

- Relié à `Patient`.
- Relié à `Medecin`.
- Peut être relié à une disponibilité.
- Vérifie les chevauchements de RDV actifs pour un même médecin.

Les dashboards patient et médecin dépendent fortement de ce modèle.

### Disponibilités

`disponibilites.models.Disponibilite`

- Reliée à un médecin.
- Définit une date, heure début, heure fin, statut et type de créneau.
- Vérifie les chevauchements de disponibilité pour un même médecin.

Le détail médecin affiche les disponibilités libres.

### Paiements

`paiements.models.Paiement`

- Peut être relié à un rendez-vous.
- Peut être relié à une consultation.
- Contient montant, devise, mode et statut.

Les vues de paiement filtrent selon le rôle :

- patient : paiements liés à ses RDV ou consultations ;
- médecin : paiements liés à ses RDV ou consultations ;
- admin : tout.

### Notifications

`notifications.models.Notification`

- Reliée à `users.User`.
- Peut être reliée à un rendez-vous.
- Sert à notifier RDV, annulations et paiements.

Les notifications non lues sont affichées dans la navbar.

### Rapports

`rapports.views.DashboardAdminView`

- Calcule des statistiques globales :
  - total patients ;
  - nouveaux patients du mois ;
  - total médecins ;
  - RDV du jour ;
  - revenus du mois.[text](ANALYSE_CODE_MEMBRES.md)

Ce dashboard est la destination des utilisateurs `admin` ou `is_staff`.

### Seed

`users/management/commands/seed_healthconnect.py`

Commande de génération de données de démonstration.

Elle crée :

- spécialités ;
- médecins ;
- patients ;
- disponibilités ;
- rendez-vous ;
- consultations ;
- paiements ;
- notifications ;
- rapports ;
- compte admin seed.

Options importantes :

- `--medecins`
- `--patients`
- `--jours`
- `--password`
- `--seed`
- `--reset`

La commande génère aussi des avatars PNG pour les utilisateurs seedés.

## 9. Flux fonctionnels principaux

### 9.1 Inscription publique patient

1. L'utilisateur va sur `/users/register/`.
2. Il choisit le rôle patient.
3. `RegisterForm` crée un `User` avec `role='patient'`.
4. Le signal `users.signals.create_role_profile` crée un `Patient`.
5. Le signal `consultations.signals.creer_dossier_medical` crée un `DossierMedical`.
6. L'utilisateur est connecté.
7. `DashboardRedirectView` l'envoie vers `patients:dashboard`.

### 9.2 Inscription publique médecin

1. L'utilisateur va sur `/users/register/`.
2. Il choisit le rôle médecin.
3. `RegisterForm` crée un `User` avec `role='medecin'`.
4. Le signal crée un `Medecin` avec numéro d'ordre automatique.
5. L'utilisateur est connecté.
6. `DashboardRedirectView` l'envoie vers `medecins:dashboard`.

### 9.3 Connexion

1. L'utilisateur saisit email et mot de passe.
2. `LoginView` appelle `authenticate(request, username=email, password=password)`.
3. Django utilise le modèle `User` où `USERNAME_FIELD = 'email'`.
4. L'utilisateur est connecté.
5. Il est redirigé vers son dashboard.

### 9.4 Création admin d'un patient

1. Un admin ouvre `/patients/creer/`.
2. Il remplit le formulaire compte + profil médical.
3. La vue crée le `User` patient.
4. La vue crée ensuite le `Patient`.

Attention : ce flux entre en conflit avec le signal qui crée déjà un `Patient`. Voir la section "risques détectés".

### 9.5 Création admin d'un médecin

1. Un admin ouvre `/medecins/creer/`.
2. Il remplit le compte + profil médecin + spécialités.
3. La vue crée le `User` médecin.
4. La vue crée ensuite le `Medecin`.

Attention : ce flux entre en conflit avec le signal qui crée déjà un `Medecin`. Voir la section "risques détectés".

## 10. Analyse des commits liés aux membres

### 10.1 `e62a765` - 18/04/2026 - `implementation backend`

Auteur : `elhadjmamadou`

Ce commit pose la base backend :

- création du modèle `users.User` ;
- création du modèle `patients.Patient` ;
- création des modèles `medecins.Specialite` et `medecins.Medecin` ;
- migrations initiales ;
- enregistrement admin ;
- configuration Django de base ;
- activation de `AUTH_USER_MODEL = 'users.User'`.

Impact :

- le projet passe d'un Django simple à une application avec utilisateurs personnalisés ;
- le rôle patient/médecin/admin devient une donnée centrale ;
- les profils patient et médecin deviennent des tables séparées.

### 10.2 `1c05a8d` - 18/04/2026 - `implementation frontend`

Auteur : `elhadjmamadou`

Ce commit ajoute l'interface initiale :

- `users/forms.py`, `users/urls.py`, `users/mixins.py` ;
- vues de login, register, logout, redirection dashboard ;
- dashboards patient et médecin ;
- listes et détails patient/médecin ;
- templates login/register ;
- sidebar et navbar adaptées aux rôles.

Impact :

- les membres peuvent s'inscrire, se connecter et être redirigés selon leur rôle ;
- les patients et médecins ont chacun un espace visuel ;
- l'application commence à utiliser les rôles dans l'interface.

### 10.3 `f319769` - 29/05/2026 - `feat(users): authentification complète et gestion des profils`

Auteur : `Nimatoulaye Barry`

Ce commit complète l'authentification :

- ajout de `ProfileForm` ;
- ajout de `ProfileView` ;
- ajout de `PasswordChangeView` ;
- ajout du flow password reset ;
- ajout des templates de profil et changement de mot de passe ;
- ajout du premier signal d'auto-création de profil médecin ;
- chargement des signaux via `UsersConfig.ready()`.

Impact :

- l'utilisateur connecté peut gérer son profil ;
- le médecin créé à l'inscription reçoit un profil automatiquement ;
- les bases du reset password sont ajoutées.

### 10.4 `976a247` - 02/06/2026 - `feat: TÂCHE 3 - Module Consultations`

Auteur : `Baldé`

Ce commit touche indirectement le code membre :

- ajout de boutons "Créer consultation" dans `templates/medecins/dashboard_medecin.html`.

Impact :

- le dashboard médecin devient un point d'entrée vers la création de consultations ;
- les RDV du médecin sont reliés au workflow médical.

### 10.5 `7e81c73` - 02/06/2026 - `implementation de system de notification`

Auteur : `Oumou Sy`

Ce commit touche :

- `config/settings/base.py` ;
- `templates/components/navbar.html`.

Impact :

- la navbar commence à afficher des informations de notification pour les membres connectés.

### 10.6 `ef1e60c` - 02/06/2026 - `fix(users): supprimer doublon ProfileView et URLs password-reset, ajouter signal Patient`

Auteur : `elhadjmamadou`

Ce commit corrige et étend :

- suppression d'un import inutile ;
- correction du context processor notifications ;
- amélioration de la navbar ;
- amélioration des templates login/register ;
- transformation du signal médecin en signal rôle complet ;
- ajout de la création automatique du profil patient.

Avant ce commit, seul le profil médecin était créé automatiquement. Après ce commit :

- un patient créé à l'inscription reçoit aussi un profil patient ;
- le signal utilise `get_or_create()` au lieu d'une création directe.

Impact :

- l'inscription patient devient cohérente avec l'inscription médecin ;
- les templates peuvent supposer que `request.user.patient_profile` existe pour un patient récent.

### 10.7 `216c247` - 02/06/2026 - `fix(login): corriger URL password_reset -> users:password_reset`

Auteur : `elhadjmamadou`

Ce commit corrige le lien "Mot de passe oublié ?" dans `templates/users/login.html`.

Impact :

- le lien utilise le namespace `users`, ce qui est nécessaire parce que les URLs users sont incluses avec `namespace="users"`.

### 10.8 `de2bde2` - 02/06/2026 - `fix(sidebar): corriger rapports:analytiques supprimé et liens # morts`

Auteur : `elhadjmamadou`

Ce commit corrige des liens dans la sidebar.

Impact :

- la navigation admin devient plus stable.

### 10.9 `dd71080` - 02/06/2026 - `fix(consultations): ajouter MonDossierView et corriger lien sidebar patient`

Auteur : `elhadjmamadou`

Ce commit corrige le lien patient vers son dossier médical.

Impact :

- le menu patient pointe vers `consultations:mon_dossier`.

### 10.10 `b49488f` - 06/06/2026 - `feat: CRUD médecins/patients, vues dossiers et améliorations UI`

Auteur : `elhadjmamadou`

Ce commit est le plus important pour le code membre récent.

Ajouts principaux :

- `patients/forms.py` ;
- `medecins/forms.py` ;
- vues créer/modifier/supprimer patient ;
- vues créer/modifier/supprimer médecin ;
- gestion des spécialités ;
- templates créer/modifier patient ;
- templates créer/modifier médecin ;
- template spécialités ;
- commande `seed_healthconnect.py`.

Impact :

- les admins peuvent gérer les patients et médecins depuis l'interface ;
- le système peut générer un jeu de données complet ;
- la partie membre passe d'un affichage/liste à un vrai CRUD.

## 11. Répartition du travail par membre

Cette partie sert à aider chaque membre à comprendre ce qu'il a fait dans le projet. Elle est basée sur l'historique Git, donc sur les commits réellement présents dans le dépôt.

### 11.1 Mamadou / `elhadjmamadou` / `Elhadj Mamadou Diallo`

Dans Git, Mamadou apparaît sous plusieurs identités :

- `elhadjmamadou <houssary356@gmail.com>`
- `Elhadj Mamadou Diallo <151888147+elhadjmamadou@users.noreply.github.com>`

Les commits de merge sous le nom `Elhadj Mamadou Diallo` servent surtout à intégrer les branches des autres membres. Les commits directs `elhadjmamadou` contiennent la majorité du socle du projet et plusieurs corrections.

Commits principaux :

- `e62a765` : `implementation backend`
- `1c05a8d` : `implementation frontend`
- `ef1e60c` : correction users, signal patient, notifications et templates
- `216c247` : correction du namespace `users:password_reset`
- `de2bde2` : correction de liens sidebar
- `dd71080` : ajout de `MonDossierView` et correction du lien patient
- `05ed6f3` : dashboard admin avec KPIs et graphiques
- `b49488f` : CRUD médecins/patients, spécialités, vues dossiers et commande seed

Tâches effectuées :

- Mise en place de la base Django du projet.
- Création de la configuration `config/settings`.
- Création du modèle utilisateur personnalisé `users.User`.
- Création des modèles métier principaux : `Patient`, `Medecin`, `Specialite`.
- Création des migrations initiales.
- Ajout des dashboards patient, médecin et admin.
- Mise en place des routes `users`, `patients`, `medecins`, puis des routes des autres modules.
- Création des pages login/register.
- Création de la sidebar et de la navbar selon les rôles.
- Ajout des formulaires et vues CRUD pour créer, modifier et supprimer patients/médecins.
- Ajout de la gestion des spécialités médecins.
- Ajout de la commande `seed_healthconnect.py` pour générer des données de démonstration.
- Corrections de navigation : password reset, sidebar, dossier patient.
- Améliorations UI : chips, layout, liens morts.

Code à lire pour comprendre son travail :

- `config/settings/base.py`
- `config/urls.py`
- `users/models.py`
- `users/forms.py`
- `users/views.py`
- `users/mixins.py`
- `users/signals.py`
- `patients/models.py`
- `patients/forms.py`
- `patients/views.py`
- `medecins/models.py`
- `medecins/forms.py`
- `medecins/views.py`
- `rapports/views.py`
- `templates/components/sidebar.html`
- `templates/components/navbar.html`
- `templates/users/login.html`
- `templates/users/register.html`
- `templates/patients/*`
- `templates/medecins/*`
- `users/management/commands/seed_healthconnect.py`

Explication du code :

Mamadou a posé la structure générale du projet. Le fichier le plus important pour les membres est `users/models.py`, car il définit le compte commun. Au lieu d'avoir des comptes séparés pour patient et médecin, le projet utilise un seul modèle `User` avec un champ `role`. Ensuite, selon ce rôle, l'utilisateur reçoit un profil `Patient` ou `Medecin`.

Dans `patients/models.py`, il a défini les informations médicales simples du patient : date de naissance, sexe, groupe sanguin, allergies, antécédents. Dans `medecins/models.py`, il a défini les informations du médecin : numéro d'ordre, tarif, mode d'exercice, spécialités et disponibilité à recevoir de nouveaux patients.

Dans `users/views.py`, Mamadou a mis en place la logique de connexion, inscription, déconnexion et redirection selon le rôle. La méthode à comprendre est `DashboardRedirectView` : elle regarde le rôle de l'utilisateur et l'envoie vers le bon tableau de bord.

Dans `patients/views.py` et `medecins/views.py`, il a ajouté les dashboards et les pages CRUD. Les vues de création utilisent deux formulaires : un formulaire pour le compte `User`, puis un formulaire pour le profil métier. C'est important parce qu'un patient/médecin est toujours composé de deux parties : identité de connexion + informations métier.

Dans `users/management/commands/seed_healthconnect.py`, Mamadou a ajouté une commande de démonstration très complète. Elle permet de générer des médecins, patients, rendez-vous, consultations, paiements, notifications et rapports pour tester le projet avec des données réalistes.

Ce que Mamadou doit pouvoir expliquer :

- pourquoi `User` est le modèle central ;
- comment le champ `role` pilote toute l'application ;
- pourquoi `Patient` et `Medecin` sont en `OneToOneField` avec `User` ;
- comment les dashboards récupèrent leurs données ;
- comment les formulaires de création créent à la fois le compte et le profil ;
- comment la sidebar change selon le rôle ;
- comment la commande seed génère des données de test.

Point à surveiller dans son code :

- Les vues admin de création patient/médecin peuvent entrer en conflit avec le signal `users.signals`, car le signal crée déjà un profil dès que le `User` est créé.
- Le formulaire public `RegisterForm` expose actuellement tous les choix de `User.Role`, y compris `admin`.

### 11.2 Nimatoulaye Barry

Commits liés :

- `f319769` : `feat(users): authentification complète et gestion des profils`
- `6eb9001` : merge de la branche d'authentification sous le compte `n2666911-prog`

Tâches effectuées :

- Ajout de la gestion du profil utilisateur.
- Ajout de la page `profile.html`.
- Ajout de la page `password_change.html`.
- Ajout du changement de mot de passe connecté.
- Ajout du flow de reset password.
- Ajout des templates `templates/registration`.
- Ajout du signal initial de création automatique du profil médecin.
- Activation des signaux dans `users/apps.py`.
- Ajout de styles CSS pour les formulaires.

Code à lire pour comprendre son travail :

- `users/forms.py`
- `users/views.py`
- `users/urls.py`
- `users/apps.py`
- `users/signals.py`
- `templates/users/profile.html`
- `templates/users/password_change.html`
- `templates/registration/password_reset.html`
- `templates/registration/password_reset_done.html`
- `templates/registration/password_reset_confirm.html`
- `templates/registration/password_reset_complete.html`
- `static/css/custom.css`

Explication du code :

Nimatoulaye a complété la partie authentification. Avant son travail, l'utilisateur pouvait déjà se connecter et s'inscrire, mais il n'avait pas encore une vraie page pour gérer son profil ou changer son mot de passe.

Dans `users/forms.py`, elle a ajouté `ProfileForm`. Ce formulaire permet de modifier les informations simples du compte : prénom, nom, téléphone et photo. Il ne modifie pas le rôle, ce qui est correct pour une page profil utilisateur.

Dans `users/views.py`, elle a ajouté `ProfileView`. Cette vue affiche le formulaire en `GET`, puis sauvegarde les modifications en `POST`. Elle a aussi ajouté `PasswordChangeView`, qui utilise `PasswordChangeForm` de Django. Le point important est `update_session_auth_hash()` : sans cette fonction, l'utilisateur serait déconnecté après avoir changé son mot de passe.

Dans `users/urls.py`, elle a ajouté les routes du profil, du changement de mot de passe et du reset password. Le reset password utilise les vues intégrées de Django.

Dans `users/signals.py`, elle a introduit l'idée d'un profil créé automatiquement après création du compte. Au départ, ce signal ne créait que le profil médecin ; plus tard, Mamadou l'a étendu au patient.

Ce que Nimatoulaye doit pouvoir expliquer :

- comment `ProfileForm` limite les champs modifiables ;
- pourquoi `ProfileView` utilise `request.user` ;
- comment `PasswordChangeForm` sécurise le changement de mot de passe ;
- pourquoi `update_session_auth_hash()` est nécessaire ;
- comment les vues Django intégrées gèrent le reset password ;
- comment `UsersConfig.ready()` charge les signaux.

Point à surveiller :

- Le code référence `registration/password_reset_email.html` et `registration/password_reset_subject.txt`, mais ces fichiers ne sont pas présents dans le dépôt.

### 11.3 Oumou Sy

Commit lié :

- `7e81c73` : `implementation de system de notification`

Tâches effectuées :

- Ajout du système de notifications.
- Ajout du context processor des notifications non lues.
- Ajout de l'envoi email de notification.
- Ajout des signaux sur rendez-vous et paiements.
- Mise à jour de la navbar pour afficher le badge de notifications.
- Ajout du template email de notification.
- Mise à jour de la liste des notifications.

Code à lire pour comprendre son travail :

- `notifications/models.py`
- `notifications/context_processors.py`
- `notifications/email_sender.py`
- `notifications/signals.py`
- `notifications/views.py`
- `notifications/urls.py`
- `templates/components/navbar.html`
- `templates/notifications/liste_notifications.html`
- `templates/notifications/email/notification.html`
- `config/settings/base.py`

Explication du code :

Oumou a travaillé sur la communication avec les membres. Le but est qu'un utilisateur reçoive une notification quand une action importante arrive : création d'un rendez-vous, confirmation, annulation ou paiement confirmé.

Dans `notifications/signals.py`, le code utilise `pre_save` et `post_save`. Le `pre_save` sert à mémoriser l'ancien statut d'un rendez-vous ou d'un paiement. Le `post_save` compare ensuite l'ancien statut avec le nouveau. Si le statut a changé vers une valeur importante, le code crée une notification.

Exemple : quand un médecin confirme un rendez-vous, le patient reçoit une notification de confirmation. Quand un rendez-vous est annulé, l'autre partie reçoit une notification d'annulation.

Dans `notifications/context_processors.py`, le code calcule le nombre de notifications non lues. Grâce au context processor, cette valeur est disponible dans tous les templates, notamment dans `templates/components/navbar.html`. C'est ce qui permet d'afficher le badge dans la cloche de notifications.

Dans `notifications/views.py`, les vues permettent à l'utilisateur de voir ses notifications, de marquer une notification comme lue, de tout marquer comme lu ou de supprimer une notification.

Ce qu'Oumou doit pouvoir expliquer :

- pourquoi les notifications sont liées à `users.User` ;
- comment un signal Django détecte un changement de statut ;
- pourquoi il faut mémoriser l'ancien statut avant sauvegarde ;
- comment le badge de notifications arrive dans la navbar ;
- pourquoi les vues filtrent toujours par `utilisateur=request.user`.

### 11.4 Baldé

Commit lié :

- `976a247` : `feat: TÂCHE 3 - Module Consultations (création & édition par le médecin)`

Tâches effectuées :

- Création de `ConsultationForm`.
- Ajout de la création de consultation depuis un rendez-vous.
- Ajout de la modification de consultation par le médecin.
- Ajout du détail d'une consultation.
- Ajout des templates de création, édition et détail de consultation.
- Mise à jour du dashboard médecin avec le bouton "Consultation".
- Mise à jour du signal qui marque le rendez-vous comme terminé après création d'une consultation.

Code à lire pour comprendre son travail :

- `consultations/forms.py`
- `consultations/views.py`
- `consultations/signals.py`
- `consultations/urls.py`
- `templates/consultations/creer_consultation.html`
- `templates/consultations/editer_consultation.html`
- `templates/consultations/detail_consultation.html`
- `templates/medecins/dashboard_medecin.html`

Explication du code :

Baldé a ajouté le coeur médical du projet : la consultation. Une consultation représente ce que le médecin écrit après ou pendant un rendez-vous : compte rendu, diagnostic, prescription et observations.

Dans `consultations/forms.py`, `ConsultationForm` expose seulement les champs médicaux que le médecin doit remplir. Le formulaire ne demande pas le patient, le médecin ou le rendez-vous, parce que ces informations sont déduites automatiquement par la vue.

Dans `CreerConsultationView`, le médecin crée une consultation à partir d'un rendez-vous. La vue vérifie d'abord que le rendez-vous appartient bien au médecin connecté. Ensuite, elle attache automatiquement :

- le dossier médical du patient ;
- le médecin connecté ;
- le rendez-vous concerné ;
- la date de consultation.

Dans `EditerConsultationView`, le médecin ne peut modifier que ses propres consultations. Cette protection est faite dans `get_queryset()`.

Dans `DetailConsultationView`, l'accès est filtré selon le rôle :

- admin : peut voir toutes les consultations ;
- médecin : peut voir ses consultations ;
- patient : peut voir ses propres consultations.

Ce que Baldé doit pouvoir expliquer :

- pourquoi le formulaire ne contient que les champs médicaux ;
- comment la vue retrouve le patient depuis le rendez-vous ;
- pourquoi la vue vérifie que le RDV appartient au médecin connecté ;
- comment le rendez-vous passe à `termine` après création de la consultation ;
- comment `get_queryset()` protège l'accès aux consultations.

Point à surveiller :

- Dans l'état actuel, `SupprimerConsultationView` utilise `messages.success`, mais `messages` n'est pas importé dans `consultations/views.py`.

### 11.5 `lamrana`

Commit lié :

- `f268c2f` : `Implement RDV detail, confirm/refuse actions and doctor availability edit/delete flows`

Tâches effectuées :

- Ajout du détail d'un rendez-vous.
- Ajout de la confirmation d'un rendez-vous par le médecin.
- Ajout du refus d'un rendez-vous par le médecin.
- Ajout de l'annulation d'un rendez-vous.
- Ajout de la modification et suppression des disponibilités médecin.
- Mise à jour des templates RDV et disponibilités.

Code à lire pour comprendre son travail :

- `rendez_vous/views.py`
- `rendez_vous/urls.py`
- `templates/rendez_vous/detail_rdv.html`
- `templates/rendez_vous/liste_rdv.html`
- `disponibilites/views.py`
- `disponibilites/urls.py`
- `templates/disponibilites/liste_disponibilites.html`

Explication du code :

`lamrana` a travaillé sur le cycle de vie du rendez-vous. Le rendez-vous commence souvent en `en_attente`, puis le médecin peut le confirmer ou le refuser. Le patient ou le médecin peut aussi annuler un rendez-vous si son statut le permet.

Dans `rendez_vous/views.py`, `RendezVousAccessMixin` vérifie que l'utilisateur connecté a le droit de voir le rendez-vous. Le patient ne peut voir que ses propres rendez-vous. Le médecin ne peut voir que les rendez-vous qui lui appartiennent.

`ConfirmerRDVView` passe le statut du rendez-vous de `en_attente` à `confirme`. `RefuserRDVView` passe le rendez-vous à `annule_medecin`. `AnnulerRDVView` choisit le statut selon la personne qui annule : `annule_patient` ou `annule_medecin`.

Dans `disponibilites/views.py`, le médecin peut ajouter, modifier et supprimer ses créneaux. La modification et la suppression sont limitées aux créneaux libres. Cela évite de modifier un créneau déjà réservé.

Ce que `lamrana` doit pouvoir expliquer :

- comment un rendez-vous change de statut ;
- pourquoi seul le médecin concerné peut confirmer/refuser ;
- pourquoi `RendezVousAccessMixin` protège l'accès au détail ;
- pourquoi une disponibilité réservée ne doit pas être modifiée ou supprimée ;
- comment les messages Django informent l'utilisateur après l'action.

### 11.6 Laye Moussa Camara

Commits liés :

- `514321b` : ajout de WeasyPrint
- `b262d08` : module rapports, vues, formulaire et URLs
- `4250979` : templates rapports et PDF
- `4525979` : lien Rapports dans la sidebar admin

Tâches effectuées :

- Ajout de la dépendance WeasyPrint.
- Création du formulaire de génération de rapport.
- Création des vues de liste, génération, téléchargement et suppression de rapports.
- Création des templates HTML de rapports.
- Création des templates PDF.
- Ajout du lien Rapports dans la sidebar admin.

Code à lire pour comprendre son travail :

- `requirements.txt`
- `rapports/forms.py`
- `rapports/views.py`
- `rapports/urls.py`
- `rapports/models.py`
- `templates/rapports/generer_rapport.html`
- `templates/rapports/liste_rapports.html`
- `templates/rapports/pdf/rapport_base.html`
- `templates/rapports/pdf/rapport_activite.html`
- `templates/components/sidebar.html`

Explication du code :

Laye Moussa a travaillé sur le module rapports. Ce module sert surtout aux administrateurs. Il permet de choisir un type de rapport et une période, puis de générer un fichier PDF.

Dans `rapports/forms.py`, `RapportForm` demande le type de rapport, la date de début et la date de fin. La méthode `clean()` vérifie que la date de fin est bien après la date de début.

Dans `rapports/views.py`, la fonction `collecter_statistiques()` calcule les chiffres utiles : rendez-vous, paiements, médecins, patients, nouveaux patients, nouveaux médecins. Ensuite, `GenererRapportView` transforme un template HTML en PDF avec WeasyPrint.

Le fichier PDF est enregistré dans le champ `fichier` du modèle `RapportGenere`. Les vues `TelechargerRapportView` et `SupprimerRapportView` permettent ensuite de récupérer ou supprimer le rapport.

Ce que Laye Moussa doit pouvoir expliquer :

- pourquoi le formulaire vérifie les dates ;
- comment les statistiques sont calculées ;
- comment un template HTML devient un PDF ;
- où le fichier PDF est sauvegardé ;
- pourquoi les rapports sont réservés aux admins/staff.

### 11.7 `ibsanba33-sudo`

Commit lié :

- `e37eccb` : `Create python-app.yml`

Tâche effectuée :

- Ajout d'un workflow GitHub Actions pour vérifier le projet automatiquement.

Code à lire :

- `.github/workflows/python-app.yml`

Explication du code :

Ce membre a ajouté une configuration CI. Le workflow se lance sur `push` et `pull_request` vers `main`. Il installe Python 3.10, installe les dépendances, lance `flake8`, puis lance `pytest`.

Ce que `ibsanba33-sudo` doit pouvoir expliquer :

- pourquoi une CI est utile dans un projet d'équipe ;
- ce que fait `actions/checkout` ;
- pourquoi on installe les dépendances depuis `requirements.txt` ;
- pourquoi `flake8` vérifie la syntaxe et certains problèmes de code ;
- pourquoi `pytest` sert à lancer les tests.

Point à surveiller :

- Le dépôt contient peu de tests réels, donc `pytest` ne valide pas encore beaucoup de comportements métier.

### 11.8 Résumé par personne

| Membre Git | Partie principale | Fichiers principaux |
| --- | --- | --- |
| Mamadou / `elhadjmamadou` | Socle projet, membres, UI, CRUD, seed, corrections | `users/*`, `patients/*`, `medecins/*`, `templates/*`, `seed_healthconnect.py` |
| Nimatoulaye Barry | Profil utilisateur, changement mot de passe, reset password | `users/forms.py`, `users/views.py`, `templates/users/*`, `templates/registration/*` |
| Oumou Sy | Notifications applicatives et email | `notifications/*`, `templates/components/navbar.html` |
| Baldé | Consultations médicales | `consultations/forms.py`, `consultations/views.py`, `templates/consultations/*` |
| `lamrana` | Cycle de vie RDV et disponibilités médecin | `rendez_vous/views.py`, `disponibilites/views.py`, templates associés |
| Laye Moussa Camara | Rapports PDF admin | `rapports/*`, `templates/rapports/*` |
| `ibsanba33-sudo` | CI GitHub Actions | `.github/workflows/python-app.yml` |

## 12. Points forts du code

- Séparation claire entre compte commun (`User`) et profils métier (`Patient`, `Medecin`).
- Utilisation correcte de `AUTH_USER_MODEL`.
- Rôles exposés sous forme de propriétés simples (`is_patient`, `is_medecin`, `is_admin_role`).
- Vues class-based lisibles et cohérentes.
- Usage de `select_related` et `prefetch_related` dans plusieurs listes pour limiter les requêtes.
- `transaction.atomic` sur les créations/modifications composées.
- Sidebar et dashboards cohérents avec les rôles.
- Commande de seed très complète pour démonstration.

## 13. Risques et problèmes détectés

### 13.1 Risque critique : inscription publique peut créer un rôle admin

`RegisterForm` expose :

```python
role = forms.ChoiceField(choices=User.Role.choices, initial=User.Role.PATIENT)
```

Comme `User.Role.choices` contient aussi `admin`, un utilisateur peut envoyer manuellement `role=admin` dans la requête POST, même si le template n'affiche que patient et médecin.

Conséquence :

- l'utilisateur obtient `is_admin_role == True` ;
- `DashboardRedirectView` l'envoie vers le dashboard admin ;
- `AdminRequiredMixin` autorise aussi `is_admin_role`.

Correction recommandée :

- limiter le formulaire public à patient/médecin seulement ;
- ne jamais permettre `admin` dans l'inscription publique ;
- créer les admins uniquement via admin Django, commande de management ou superuser.

### 13.2 Risque critique : conflit entre signal et CRUD admin

Le signal `users.signals.create_role_profile` crée automatiquement un `Patient` ou un `Medecin` dès que le `User` est sauvegardé.

Mais `CreerPatientView` et `CreerMedecinView` font aussi :

```python
user = user_form.save()
patient = profile_form.save(commit=False)
patient.user = user
patient.save()
```

et :

```python
user = user_form.save()
medecin = profile_form.save(commit=False)
medecin.user = user
medecin.save()
```

Comme la relation `User -> Patient` et `User -> Medecin` est en `OneToOneField`, il ne peut pas y avoir deux profils pour le même utilisateur.

Conséquence probable :

- création admin patient : risque d'`IntegrityError` ;
- création admin médecin : risque d'`IntegrityError`.

Correction recommandée :

- soit le signal crée toujours le profil, et les vues admin doivent récupérer le profil existant puis le mettre à jour ;
- soit les vues créent les profils, et le signal doit être limité au flux d'inscription publique ;
- soit utiliser une logique `update_or_create()` dans les vues de création admin.

### 13.3 Fichiers manquants pour reset password

`users/urls.py` référence :

```python
email_template_name='registration/password_reset_email.html'
subject_template_name='registration/password_reset_subject.txt'
```

Mais ces deux fichiers ne sont pas présents dans le dépôt.

Conséquence :

- le reset password peut échouer au moment d'envoyer l'email.

Correction recommandée :

- ajouter `templates/registration/password_reset_email.html` ;
- ajouter `templates/registration/password_reset_subject.txt`.

### 13.4 Accès trop large aux patients

`ListePatientsView` et `DetailPatientView` utilisent seulement `LoginRequiredMixin`.

Conséquence :

- n'importe quel utilisateur connecté peut ouvrir la liste des patients si l'URL est connue ;
- n'importe quel utilisateur connecté peut potentiellement consulter le détail d'un patient.

Correction recommandée :

- limiter la liste complète aux admins et médecins ;
- limiter le détail patient :
  - admin : tous ;
  - médecin : patients liés à ses RDV/consultations ;
  - patient : uniquement son propre dossier.

### 13.5 Accès admin applicatif différent de `is_staff`

Le projet considère `role='admin'` comme admin applicatif, même si `is_staff=False`.

Ce choix peut être volontaire, mais il devient dangereux avec l'inscription publique.

Correction recommandée :

- clarifier la politique :
  - soit `role='admin'` suffit pour l'admin applicative ;
  - soit il faut aussi `is_staff=True`.

### 13.6 Liens de modification médecin incohérents

Dans `templates/medecins/liste_medecins.html`, certaines actions admin pointent directement vers `/admin/medecins/medecin/...`.

Mais le projet possède maintenant des routes custom :

- `medecins:modifier`
- `medecins:supprimer`

Correction recommandée :

- utiliser les routes custom dans la liste, comme dans la page détail.

### 13.7 Tests absents

Les fichiers :

- `users/tests.py`
- `patients/tests.py`
- `medecins/tests.py`

ne contiennent que le squelette Django.

Tests prioritaires à ajouter :

- inscription patient crée `User`, `Patient`, `DossierMedical` ;
- inscription médecin crée `User`, `Medecin` ;
- inscription publique refuse `role=admin` ;
- création admin patient ne crée pas de doublon ;
- création admin médecin ne crée pas de doublon ;
- patient ne peut pas voir le dossier d'un autre patient ;
- médecin ne peut voir que les patients liés à lui.

## 14. Résumé final

Le code membre est structuré autour d'un modèle `User` personnalisé et de deux profils métier en relation `OneToOne` : `Patient` et `Medecin`. Les rôles pilotent la navigation, les dashboards et les droits d'accès. Les commits montrent une progression claire : backend initial, interface de connexion/dashboards, gestion du profil et du mot de passe, notifications, puis CRUD complet patient/médecin et génération de données.

Les deux points les plus importants à corriger avant une mise en production sont :

1. empêcher la création d'un compte admin depuis l'inscription publique ;
2. résoudre le conflit entre les signaux de création automatique de profils et les vues admin de création patient/médecin.
