from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from textwrap import dedent

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from consultations.models import Consultation, DossierMedical
from disponibilites.models import Disponibilite
from medecins.models import Medecin, Specialite
from notifications.models import Notification
from paiements.models import ConfigurationDjomy, Paiement
from patients.models import Patient
from rapports.models import RapportGenere
from rendez_vous.models import RendezVous
from users.models import User

SEED_EMAIL_DOMAIN = "seed.healthconnect.local"
SEEDED_IMAGE_DIR = Path(settings.MEDIA_ROOT) / "users" / "photos" / "seeded"
REPORTS_DIR = Path(settings.MEDIA_ROOT) / "rapports"

SPECIALITES = [
    {
        "libelle": "Cardiologie",
        "description": "Prise en charge des maladies cardiovasculaires, du suivi tensionnel et des bilans cardiaques.",
        "icone": "bi-heart-pulse",
    },
    {
        "libelle": "Dermatologie",
        "description": "Consultations de la peau, du cuir chevelu et des phaneres avec suivi des lesions chroniques.",
        "icone": "bi-bandaid",
    },
    {
        "libelle": "Gynecologie",
        "description": "Suivi gynecologique, depistage, consultation de fertilite et suivi hormonal.",
        "icone": "bi-gender-female",
    },
    {
        "libelle": "Pediatrie",
        "description": "Suivi de croissance, vaccination, pathologies courantes et surveillance du nourrisson.",
        "icone": "bi-balloon-heart",
    },
    {
        "libelle": "Medecine generale",
        "description": "Premier recours, orientation clinique, suivi de pathologies chroniques et prevention.",
        "icone": "bi-hospital",
    },
    {
        "libelle": "Neurologie",
        "description": "Evaluation des troubles neurologiques, migraines, neuropathies et suivi post-AVC.",
        "icone": "bi-activity",
    },
    {
        "libelle": "Ophtalmologie",
        "description": "Troubles visuels, suivi de la pression oculaire et bilan de la vue.",
        "icone": "bi-eye",
    },
    {
        "libelle": "ORL",
        "description": "Affections de l'oreille, du nez, de la gorge et troubles de l'audition.",
        "icone": "bi-ear",
    },
]

MEDECIN_PROFILES = [
    ("Aissatou", "Camara", "F"),
    ("Mamadou", "Diallo", "M"),
    ("Fatoumata", "Bah", "F"),
    ("Ibrahima", "Sow", "M"),
    ("Mariama", "Keita", "F"),
    ("Abdoulaye", "Barry", "M"),
    ("Kadiatou", "Sylla", "F"),
    ("Ousmane", "Balde", "M"),
    ("Aminata", "Kourouma", "F"),
    ("Moussa", "Cisse", "M"),
    ("Nabintou", "Traore", "F"),
    ("Salif", "Conde", "M"),
]

PRENOMS_MASCULINS = [
    "Mamadou", "Ibrahima", "Ousmane", "Sekou", "Alpha", "Mohamed", "Fode", "Siaka",
    "Sory", "Salif", "Moussa", "Lansana", "Youssouf", "Amadou", "Mamady", "Boubacar",
    "Tierno", "Abdoulaye", "Mouctar", "Oumar", "Aliou", "Issiaga", "Bourama", "Karamo",
]

PRENOMS_FEMININS = [
    "Aissatou", "Aminata", "Fatoumata", "Kadiatou", "Hawa", "Mariama", "Binta", "Khady",
    "Nafissatou", "Ramatoulaye", "Maimouna", "Aicha", "Adama", "Fanta", "Nene", "Assetou",
    "Rabiatou", "Nabintou", "Hadja", "Mariam", "Saran", "Kadiatou", "Kadidiatou", "Fadima",
]

NOMS_FAMILLE = [
    "Camara", "Diallo", "Bah", "Sow", "Keita", "Barry", "Sylla", "Balde", "Kourouma",
    "Cisse", "Traore", "Conde", "Bangoura", "Fofana", "Diane", "Konte", "Toure", "Sacko",
    "Kouyate", "Doumbouya", "Kaba", "Soumah", "Mane", "Yansane", "Dioubate", "Sama",
]

PATIENT_PROFILES = [
    ("Moussa", "Camara", "M"),
    ("Aicha", "Diallo", "F"),
    ("Boubacar", "Bah", "M"),
    ("Kadiatou", "Sow", "F"),
    ("Ibrahima", "Barry", "M"),
    ("Hawa", "Sylla", "F"),
    ("Mamadou", "Conde", "M"),
    ("Fatou", "Keita", "F"),
    ("Mory", "Balde", "M"),
    ("Aminata", "Cisse", "F"),
    ("Sekou", "Traore", "M"),
    ("Saran", "Kaba", "F"),
    ("Abdoulaye", "Doumbouya", "M"),
    ("Assetou", "Bangoura", "F"),
    ("Oumar", "Fofana", "M"),
    ("Nene", "Diane", "F"),
    ("Alpha", "Konte", "M"),
    ("Mariam", "Toure", "F"),
    ("Yacouba", "Sacko", "M"),
    ("Binta", "Kouyate", "F"),
    ("Mouctar", "Bah", "M"),
    ("Aissatou", "Camara", "F"),
    ("Seydou", "Barry", "M"),
    ("Ramatoulaye", "Sow", "F"),
    ("Fode", "Diallo", "M"),
    ("Khady", "Conde", "F"),
    ("Mohamed", "Keita", "M"),
    ("Hadja", "Sylla", "F"),
    ("Sory", "Cisse", "M"),
    ("Binta", "Bangoura", "F"),
    ("Mamadou Aliou", "Balde", "M"),
    ("Nafissatou", "Traore", "F"),
    ("Tierno", "Kourouma", "M"),
    ("Fanta", "Fofana", "F"),
    ("Moussa Moise", "Kaba", "M"),
    ("Adama", "Diane", "F"),
    ("Ibrahima Sory", "Konte", "M"),
    ("M'mah", "Toure", "F"),
    ("Mamady", "Sacko", "M"),
    ("Aicha", "Kouyate", "F"),
    ("Alseny", "Doumbouya", "M"),
    ("Fadima", "Bangoura", "F"),
    ("Lansana", "Camara", "M"),
    ("Rabiatou", "Diallo", "F"),
    ("Siaka", "Bah", "M"),
    ("Maimouna", "Barry", "F"),
    ("Salam", "Conde", "M"),
    ("Hawa", "Keita", "F"),
]

COMMUNES = [
    "Kaloum",
    "Dixinn",
    "Ratoma",
    "Matam",
    "Matoto",
    "Lambanyi",
    "Nongo",
    "Kipé",
]

RUES = [
    "Rue KA 028",
    "Axe Le Prince",
    "Corniche Nord",
    "Route de Donka",
    "Transversale T6",
    "Rue Niger",
    "Route de Dabompa",
    "Carrefour Cosa",
]

ALLERGIES = [
    "",
    "",
    "Aucune allergie signalee.",
    "Allergie legere a la penicilline.",
    "Rhinite allergique saisonniere.",
    "Reaction connue aux arachides.",
]

ANTECEDENTS = [
    "Aucun antecedent majeur. Suivi preventif regulier.",
    "Antecedent d'hypertension equilibree sous traitement.",
    "Asthme intermittent depuis l'enfance, crises rares.",
    "Cesarienne ancienne, suivi gynecologique annuel.",
    "Diabete de type 2 sous surveillance trimestrielle.",
    "Migraine episodique avec bonne reponse au traitement.",
]

MOTIFS = [
    "Controle de tension arterielle avec renouvellement de traitement.",
    "Douleurs thoraciques intermittentes depuis 48 heures.",
    "Eruption cutanee prurigineuse apparue apres un nouveau savon.",
    "Suivi de grossesse du deuxieme trimestre.",
    "Fievre et toux persistante chez un enfant de 4 ans.",
    "Troubles visuels avec fatigue oculaire en fin de journee.",
    "Otalgie droite avec baisse auditive moderee.",
    "Cefalees recurrentes avec sensibilite a la lumiere.",
    "Bilan general annuel avec fatigue passagere.",
    "Douleurs lombaires apres effort physique.",
]

DIAGNOSTICS = [
    "Hypertension arterielle stable sans signe de gravite immediate.",
    "Dermatite de contact probable sans surinfection.",
    "Suivi de grossesse evolutif rassurant.",
    "Syndrome grippal simple sans detresse respiratoire.",
    "Migraine sans aura avec facteur declenchant probable lie au stress.",
    "Conjonctivite allergique moderee.",
    "Lombalgie mecanique sans drapeau rouge.",
    "Otite externe debutante avec inflammation locale.",
]

PRESCRIPTIONS = [
    "Paracetamol si douleur, hydratation, repos et controle dans 7 jours.",
    "Antihypertenseur maintenu, auto-mesure tensionnelle matin et soir pendant 10 jours.",
    "Creme dermocorticoide locale pendant 5 jours et savon surgras.",
    "Supplementation, examens biologiques de routine et echographie de controle.",
    "Lavage nasal, antipyeretique si besoin et retour si aggravation.",
    "Larmes artificielles, pause ecran et consultation de controle dans 1 mois.",
    "Anti-inflammatoire court, exercices d'etirement et eviter le port de charge.",
]

OBSERVATIONS = [
    "Patient adherent, bonne comprehension des consignes.",
    "Surveillance clinique recommandee avec point telephonique si persistance des symptomes.",
    "Constantes rassurantes. Education therapeutique renforcee pendant la consultation.",
    "Patient accompagne, observance jugee satisfaisante.",
]


class Command(BaseCommand):
    help = "Injecte des donnees de demonstration realistes dans HealthConnect avec avatars PNG."

    def add_arguments(self, parser):
        parser.add_argument("--medecins", type=int, default=40)
        parser.add_argument("--patients", type=int, default=260)
        parser.add_argument("--jours", type=int, default=120)
        parser.add_argument("--password", default="HealthConnect123!")
        parser.add_argument("--seed", type=int, default=20260520)
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Supprime les donnees seedees avant regeneration.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        rng = random.Random(options["seed"])

        if options["reset"]:
            self._cleanup_seeded_records(clear_users=True)
        else:
            self._cleanup_seeded_records(clear_users=False)

        self._ensure_directories()

        specialites = self._seed_specialites()
        medecins = self._seed_medecins(
            count=options["medecins"],
            password=options["password"],
            specialites=specialites,
            rng=rng,
        )
        patients = self._seed_patients(
            count=options["patients"],
            password=options["password"],
            rng=rng,
        )
        medecins = self._ensure_existing_medecins(
            medecins=medecins,
            specialites=specialites,
            rng=rng,
        )
        patients = self._ensure_existing_patients(patients=patients, rng=rng)
        disponibilites = self._seed_disponibilites(
            medecins=medecins,
            jours=options["jours"],
            rng=rng,
        )
        rdvs = self._seed_rendez_vous(
            disponibilites=disponibilites,
            patients=patients,
            rng=rng,
        )
        consultations = self._seed_consultations(rdvs=rdvs, rng=rng)
        paiements = self._seed_paiements(rdvs=rdvs, consultations=consultations, rng=rng)
        notifications = self._seed_notifications(rdvs=rdvs, paiements=paiements, rng=rng)
        self._seed_configuration_djomy()
        rapports = self._seed_rapports(
            admin_user=User.objects.get(email=f"admin@{SEED_EMAIL_DOMAIN}"),
            medecins=medecins,
            patients=patients,
            rdvs=rdvs,
            paiements=paiements,
        )

        self.stdout.write(self.style.SUCCESS("Seed termine."))
        self.stdout.write(f"Specialites : {len(specialites)}")
        self.stdout.write(f"Medecins : {len(medecins)}")
        self.stdout.write(f"Patients : {len(patients)}")
        self.stdout.write(f"Disponibilites : {len(disponibilites)}")
        self.stdout.write(f"Rendez-vous : {len(rdvs)}")
        self.stdout.write(f"Consultations : {len(consultations)}")
        self.stdout.write(f"Paiements : {len(paiements)}")
        self.stdout.write(f"Notifications : {len(notifications)}")
        self.stdout.write(f"Rapports : {len(rapports)}")
        self.stdout.write(
            f"Compte admin : admin@{SEED_EMAIL_DOMAIN} / {options['password']}"
        )

    def _cleanup_seeded_records(self, *, clear_users: bool) -> None:
        seeded_users = User.objects.filter(email__iendswith=f"@{SEED_EMAIL_DOMAIN}")
        seeded_medecins = Medecin.objects.filter(user__in=seeded_users)
        seeded_patients = Patient.objects.filter(user__in=seeded_users)

        Paiement.objects.filter(
            consultation__in=Consultation.objects.filter(
                dossier__patient__in=seeded_patients
            )
        ).delete()
        Paiement.objects.filter(rendez_vous__patient__in=seeded_patients).delete()
        Notification.objects.filter(utilisateur__in=seeded_users).delete()
        Consultation.objects.filter(dossier__patient__in=seeded_patients).delete()
        Consultation.objects.filter(medecin__in=seeded_medecins).delete()
        RapportGenere.objects.filter(genere_par__in=seeded_users).delete()
        RendezVous.objects.filter(patient__in=seeded_patients).delete()
        Disponibilite.objects.filter(medecin__in=seeded_medecins).delete()

        if clear_users:
            seeded_users.delete()
            Specialite.objects.filter(
                libelle__in=[item["libelle"] for item in SPECIALITES]
            ).delete()

        if SEEDED_IMAGE_DIR.exists():
            for path in SEEDED_IMAGE_DIR.glob("*.png"):
                path.unlink(missing_ok=True)
        if REPORTS_DIR.exists():
            for path in REPORTS_DIR.glob("seed_*.txt"):
                path.unlink(missing_ok=True)

    def _ensure_directories(self) -> None:
        SEEDED_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    def _seed_specialites(self) -> list[Specialite]:
        specialites = []
        for data in SPECIALITES:
            specialite, _ = Specialite.objects.update_or_create(
                libelle=data["libelle"],
                defaults={
                    "description": data["description"],
                    "icone": data["icone"],
                },
            )
            specialites.append(specialite)
        return specialites

    def _seed_medecins(
        self,
        *,
        count: int,
        password: str,
        specialites: list[Specialite],
        rng: random.Random,
    ) -> list[Medecin]:
        medecins = []
        profiles = self._build_profiles(
            count=count,
            seed_profiles=MEDECIN_PROFILES,
            rng=rng,
        )

        admin_user, _ = User.objects.update_or_create(
            email=f"admin@{SEED_EMAIL_DOMAIN}",
            defaults={
                "username": "admin_seed",
                "first_name": "Admin",
                "last_name": "HealthConnect",
                "role": User.Role.ADMIN,
                "telephone": "+224620000001",
                "statut": User.Statut.ACTIF,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        admin_user.set_password(password)
        self._attach_avatar(admin_user, "#0f766e", "#14b8a6")
        admin_user.save()

        for index, (first_name, last_name, _) in enumerate(profiles, start=1):
            email = self._build_email(first_name, last_name, index)
            user, _ = User.objects.update_or_create(
                email=email,
                defaults={
                    "username": f"medecin_seed_{index}",
                    "first_name": first_name,
                    "last_name": last_name,
                    "role": User.Role.MEDECIN,
                    "telephone": f"+22462{index:07d}",
                    "statut": User.Statut.ACTIF,
                },
            )
            user.set_password(password)
            color_start, color_end = self._random_color_pair(rng)
            self._attach_avatar(user, color_start, color_end)
            user.save()

            medecin, _ = Medecin.objects.update_or_create(
                user=user,
                defaults={
                    "numero_ordre": f"GN-ORD-{2026 + index}-{index:03d}",
                    "biographie": (
                        f"Le Dr {first_name} {last_name} recoit en consultation "
                        "sur rendez-vous, avec une pratique orientee prevention, "
                        "suivi rigoureux et education therapeutique."
                    ),
                    "tarif_consultation": Decimal(rng.choice([150000, 180000, 200000, 250000])),
                    "mode_exercice": rng.choice(
                        [
                            Medecin.ModeExercice.LIBERAL,
                            Medecin.ModeExercice.SALARIE,
                            Medecin.ModeExercice.MIXTE,
                        ]
                    ),
                    "accepte_nouveaux_patients": rng.random() > 0.15,
                },
            )
            medecin.specialites.set(rng.sample(specialites, k=rng.choice([1, 2])))
            medecins.append(medecin)

        return medecins

    def _seed_patients(
        self,
        *,
        count: int,
        password: str,
        rng: random.Random,
    ) -> list[Patient]:
        patients = []
        profiles = self._build_profiles(
            count=count,
            seed_profiles=PATIENT_PROFILES,
            rng=rng,
        )
        groupes = [choice for choice, _ in Patient.GroupeSanguin.choices]

        for index, (first_name, last_name, sexe) in enumerate(profiles, start=1):
            email = self._build_email(first_name, last_name, index + 100)
            user, _ = User.objects.update_or_create(
                email=email,
                defaults={
                    "username": f"patient_seed_{index}",
                    "first_name": first_name,
                    "last_name": last_name,
                    "role": User.Role.PATIENT,
                    "telephone": f"+22465{index:07d}",
                    "statut": User.Statut.ACTIF,
                },
            )
            user.set_password(password)
            color_start, color_end = self._random_color_pair(rng)
            self._attach_avatar(user, color_start, color_end)
            user.save()

            patient, _ = Patient.objects.update_or_create(
                user=user,
                defaults={
                    "date_naissance": self._random_birth_date(rng),
                    "sexe": Patient.Sexe.MASCULIN if sexe == "M" else Patient.Sexe.FEMININ,
                    "adresse": f"{rng.choice(RUES)}, {rng.choice(COMMUNES)}, Conakry",
                    "groupe_sanguin": rng.choice(groupes),
                    "allergies": rng.choice(ALLERGIES),
                    "antecedents_resumes": rng.choice(ANTECEDENTS),
                },
            )
            dossier = DossierMedical.objects.get(patient=patient)
            dossier.notes_generales = (
                "Dossier de demonstration alimente avec historiques de suivi, "
                "consultations et paiements coherents."
            )
            dossier.save(update_fields=["notes_generales", "date_modification"])
            patients.append(patient)

        return patients

    def _ensure_existing_patients(
        self,
        *,
        patients: list[Patient],
        rng: random.Random,
    ) -> list[Patient]:
        existing = {patient.user_id for patient in patients}
        groupes = [choice for choice, _ in Patient.GroupeSanguin.choices]

        for user in User.objects.filter(role=User.Role.PATIENT).exclude(
            email__iendswith=f"@{SEED_EMAIL_DOMAIN}"
        ):
            if not user.first_name:
                user.first_name = rng.choice(PRENOMS_MASCULINS + PRENOMS_FEMININS)
            if not user.last_name:
                user.last_name = rng.choice(NOMS_FAMILLE)
            if not user.telephone:
                user.telephone = f"+22466{rng.randint(1000000, 9999999)}"
            if not user.photo:
                color_start, color_end = self._random_color_pair(rng)
                self._attach_avatar(user, color_start, color_end)
            user.save()

            patient, _ = Patient.objects.update_or_create(
                user=user,
                defaults={
                    "date_naissance": self._random_birth_date(rng),
                    "sexe": rng.choice([choice for choice, _ in Patient.Sexe.choices[:2]]),
                    "adresse": f"{rng.choice(RUES)}, {rng.choice(COMMUNES)}, Conakry",
                    "groupe_sanguin": rng.choice(groupes),
                    "allergies": rng.choice(ALLERGIES),
                    "antecedents_resumes": rng.choice(ANTECEDENTS),
                },
            )
            dossier = DossierMedical.objects.get(patient=patient)
            if not dossier.notes_generales:
                dossier.notes_generales = (
                    "Profil existant enrichi automatiquement pour rendre visibles "
                    "les parcours de soins, paiements et notifications."
                )
                dossier.save(update_fields=["notes_generales", "date_modification"])
            if patient.user_id not in existing:
                patients.append(patient)
                existing.add(patient.user_id)

        return patients

    def _ensure_existing_medecins(
        self,
        *,
        medecins: list[Medecin],
        specialites: list[Specialite],
        rng: random.Random,
    ) -> list[Medecin]:
        existing = {medecin.user_id for medecin in medecins}

        for user in User.objects.filter(role=User.Role.MEDECIN).exclude(
            email__iendswith=f"@{SEED_EMAIL_DOMAIN}"
        ):
            if not user.first_name:
                user.first_name = rng.choice(PRENOMS_MASCULINS + PRENOMS_FEMININS)
            if not user.last_name:
                user.last_name = rng.choice(NOMS_FAMILLE)
            if not user.telephone:
                user.telephone = f"+22467{rng.randint(1000000, 9999999)}"
            if not user.photo:
                color_start, color_end = self._random_color_pair(rng)
                self._attach_avatar(user, color_start, color_end)
            user.save()

            medecin, _ = Medecin.objects.update_or_create(
                user=user,
                defaults={
                    "numero_ordre": f"GN-REAL-{user.pk:06d}",
                    "biographie": (
                        f"Le Dr {user.get_full_name() or user.email} a ete integre "
                        "au jeu de donnees avec un planning et un historique complets."
                    ),
                    "tarif_consultation": Decimal(rng.choice([150000, 180000, 200000, 250000])),
                    "mode_exercice": rng.choice(
                        [
                            Medecin.ModeExercice.LIBERAL,
                            Medecin.ModeExercice.SALARIE,
                            Medecin.ModeExercice.MIXTE,
                        ]
                    ),
                    "accepte_nouveaux_patients": True,
                },
            )
            if medecin.specialites.count() == 0:
                medecin.specialites.set(rng.sample(specialites, k=rng.choice([1, 2])))
            if medecin.user_id not in existing:
                medecins.append(medecin)
                existing.add(medecin.user_id)

        return medecins

    def _seed_disponibilites(
        self,
        *,
        medecins: list[Medecin],
        jours: int,
        rng: random.Random,
    ) -> list[Disponibilite]:
        disponibilites = []
        today = timezone.localdate()
        start_day = today - timedelta(days=max(30, jours // 3))
        end_day = today + timedelta(days=max(1, jours))
        slots = [
            (time(8, 0), time(8, 45)),
            (time(9, 0), time(9, 45)),
            (time(10, 0), time(10, 45)),
            (time(11, 0), time(11, 45)),
            (time(14, 0), time(14, 45)),
            (time(15, 0), time(15, 45)),
            (time(16, 0), time(16, 45)),
            (time(17, 0), time(17, 45)),
        ]

        current_day = start_day
        while current_day <= end_day:
            if current_day.weekday() < 6:
                for medecin in medecins:
                    for heure_debut, heure_fin in slots:
                        if rng.random() < 0.06:
                            continue
                        disponibilites.append(
                            Disponibilite.objects.create(
                                medecin=medecin,
                                date_disponibilite=current_day,
                                heure_debut=heure_debut,
                                heure_fin=heure_fin,
                                statut_creneau=Disponibilite.StatutCreneau.LIBRE,
                                type_creneau=rng.choice(
                                    [
                                        Disponibilite.TypeCreneau.PRESENTIEL,
                                        Disponibilite.TypeCreneau.TELECONSULTATION,
                                        Disponibilite.TypeCreneau.LES_DEUX,
                                    ]
                                ),
                            )
                        )
            current_day += timedelta(days=1)
        return disponibilites

    def _seed_rendez_vous(
        self,
        *,
        disponibilites: list[Disponibilite],
        patients: list[Patient],
        rng: random.Random,
    ) -> list[RendezVous]:
        rdvs = []
        today = timezone.localdate()

        for disponibilite in disponibilites:
            booking_probability = 0.78 if disponibilite.date_disponibilite <= today else 0.52
            if rng.random() > booking_probability:
                continue

            if disponibilite.date_disponibilite < today:
                statut = rng.choices(
                    population=[
                        RendezVous.StatutRdv.TERMINE,
                        RendezVous.StatutRdv.ANNULE_PATIENT,
                        RendezVous.StatutRdv.NO_SHOW,
                    ],
                    weights=[0.79, 0.14, 0.07],
                    k=1,
                )[0]
            elif disponibilite.date_disponibilite == today:
                statut = rng.choices(
                    population=[
                        RendezVous.StatutRdv.CONFIRME,
                        RendezVous.StatutRdv.EN_ATTENTE,
                        RendezVous.StatutRdv.TERMINE,
                    ],
                    weights=[0.48, 0.32, 0.20],
                    k=1,
                )[0]
            else:
                statut = rng.choices(
                    population=[
                        RendezVous.StatutRdv.CONFIRME,
                        RendezVous.StatutRdv.EN_ATTENTE,
                        RendezVous.StatutRdv.ANNULE_MEDECIN,
                    ],
                    weights=[0.66, 0.26, 0.08],
                    k=1,
                )[0]

            rdv = RendezVous.objects.create(
                patient=rng.choice(patients),
                medecin=disponibilite.medecin,
                disponibilite=disponibilite,
                date_rdv=disponibilite.date_disponibilite,
                heure_debut=disponibilite.heure_debut,
                heure_fin=disponibilite.heure_fin,
                statut_rdv=statut,
                motif=rng.choice(MOTIFS),
                canal=rng.choice([choice for choice, _ in RendezVous.Canal.choices]),
            )

            if statut == RendezVous.StatutRdv.TERMINE:
                disponibilite.statut_creneau = Disponibilite.StatutCreneau.INDISPONIBLE
            elif statut in [RendezVous.StatutRdv.CONFIRME, RendezVous.StatutRdv.EN_ATTENTE]:
                disponibilite.statut_creneau = Disponibilite.StatutCreneau.RESERVE
            else:
                disponibilite.statut_creneau = Disponibilite.StatutCreneau.LIBRE
            disponibilite.save(update_fields=["statut_creneau", "date_modification"])
            rdvs.append(rdv)

        return rdvs

    def _seed_consultations(
        self,
        *,
        rdvs: list[RendezVous],
        rng: random.Random,
    ) -> list[Consultation]:
        consultations = []
        tz = timezone.get_current_timezone()

        for rdv in rdvs:
            if rdv.statut_rdv != RendezVous.StatutRdv.TERMINE:
                continue

            dossier = DossierMedical.objects.get(patient=rdv.patient)
            dt = datetime.combine(rdv.date_rdv, rdv.heure_debut)
            aware_dt = timezone.make_aware(dt, tz) if timezone.is_naive(dt) else dt
            consultation = Consultation.objects.create(
                dossier=dossier,
                medecin=rdv.medecin,
                rendez_vous=rdv,
                date_consultation=aware_dt,
                compte_rendu=(
                    f"Consultation realisee pour le motif suivant : {rdv.motif} "
                    "Examen clinique effectue avec conseils adaptes au contexte."
                ),
                diagnostic=rng.choice(DIAGNOSTICS),
                prescription=rng.choice(PRESCRIPTIONS),
                observations=rng.choice(OBSERVATIONS),
            )
            consultations.append(consultation)

        return consultations

    def _seed_paiements(
        self,
        *,
        rdvs: list[RendezVous],
        consultations: list[Consultation],
        rng: random.Random,
    ) -> list[Paiement]:
        paiements = []
        consultations_by_rdv = {consultation.rendez_vous_id: consultation for consultation in consultations}

        for rdv in rdvs:
            consultation = consultations_by_rdv.get(rdv.id)
            if rdv.statut_rdv == RendezVous.StatutRdv.TERMINE:
                statut = rng.choices(
                    population=[
                        Paiement.StatutPaiement.CONFIRME,
                        Paiement.StatutPaiement.REMBOURSE,
                    ],
                    weights=[0.92, 0.08],
                    k=1,
                )[0]
                date_paiement = self._combine_as_aware_datetime(rdv.date_rdv, rdv.heure_fin)
            elif rdv.statut_rdv in [RendezVous.StatutRdv.CONFIRME, RendezVous.StatutRdv.EN_ATTENTE]:
                statut = rng.choice(
                    [
                        Paiement.StatutPaiement.EN_ATTENTE,
                        Paiement.StatutPaiement.INITIE,
                    ]
                )
                date_paiement = None
            else:
                statut = rng.choice(
                    [
                        Paiement.StatutPaiement.ECHOUE,
                        Paiement.StatutPaiement.REMBOURSE,
                    ]
                )
                date_paiement = None

            paiement = Paiement.objects.create(
                rendez_vous=rdv,
                consultation=consultation,
                montant=rdv.medecin.tarif_consultation,
                devise="GNF",
                mode_paiement=rng.choice([choice for choice, _ in Paiement.ModePaiement.choices]),
                statut_paiement=statut,
                date_paiement=date_paiement,
                reference_djomy=(
                    f"DJ-{rng.randint(1000000, 9999999)}"
                    if statut in [Paiement.StatutPaiement.CONFIRME, Paiement.StatutPaiement.INITIE]
                    else ""
                ),
                webhook_payload={
                    "source": "seed",
                    "statut": statut,
                    "canal": rdv.canal,
                    "patient": rdv.patient.nom_complet,
                },
            )
            paiements.append(paiement)

            if consultation:
                paiements.extend(
                    self._seed_payment_history_for_consultation(
                        consultation=consultation,
                        primary_payment=paiement,
                        rng=rng,
                    )
                )

        return paiements

    def _seed_notifications(
        self,
        *,
        rdvs: list[RendezVous],
        paiements: list[Paiement],
        rng: random.Random,
    ) -> list[Notification]:
        notifications = []
        payments_by_rdv = {payment.rendez_vous_id: payment for payment in paiements if payment.rendez_vous_id}

        for rdv in rdvs:
            if rdv.statut_rdv in [RendezVous.StatutRdv.CONFIRME, RendezVous.StatutRdv.EN_ATTENTE]:
                notif_type = Notification.TypeNotification.CONFIRMATION_RDV
                resume = (
                    f"Votre rendez-vous avec {rdv.medecin} est programme le "
                    f"{rdv.date_rdv:%d/%m/%Y} a {rdv.heure_debut:%H:%M}."
                )
            elif rdv.statut_rdv in [RendezVous.StatutRdv.ANNULE_MEDECIN, RendezVous.StatutRdv.ANNULE_PATIENT]:
                notif_type = Notification.TypeNotification.ANNULATION_RDV
                resume = (
                    f"Le rendez-vous du {rdv.date_rdv:%d/%m/%Y} avec {rdv.medecin} "
                    "a ete annule."
                )
            else:
                notif_type = Notification.TypeNotification.INFO_GENERALE
                resume = (
                    f"Le suivi medical lie a votre consultation du "
                    f"{rdv.date_rdv:%d/%m/%Y} est disponible dans votre dossier."
                )

            notifications.append(
                Notification.objects.create(
                    utilisateur=rdv.patient.user,
                    rendez_vous=rdv,
                    type_notification=notif_type,
                    canal=rng.choice([choice for choice, _ in Notification.Canal.choices]),
                    contenu_resume=resume,
                    statut_notification=rng.choice(
                        [
                            Notification.StatutNotification.ENVOYE,
                            Notification.StatutNotification.LU,
                        ]
                    ),
                    date_lecture=timezone.now() if rng.random() > 0.45 else None,
                )
            )

            payment = payments_by_rdv.get(rdv.id)
            if not payment:
                continue

            if payment.statut_paiement == Paiement.StatutPaiement.CONFIRME:
                type_notification = Notification.TypeNotification.PAIEMENT_CONFIRME
                resume = (
                    f"Paiement confirme pour votre rendez-vous du {rdv.date_rdv:%d/%m/%Y}, "
                    f"montant {payment.montant} {payment.devise}."
                )
            elif payment.statut_paiement == Paiement.StatutPaiement.ECHOUE:
                type_notification = Notification.TypeNotification.PAIEMENT_ECHOUE
                resume = (
                    f"Echec du paiement du rendez-vous du {rdv.date_rdv:%d/%m/%Y}. "
                    "Veuillez relancer le reglement."
                )
            else:
                continue

            notifications.append(
                Notification.objects.create(
                    utilisateur=rdv.patient.user,
                    rendez_vous=rdv,
                    type_notification=type_notification,
                    canal=Notification.Canal.APPLICATION,
                    contenu_resume=resume,
                    statut_notification=Notification.StatutNotification.ENVOYE,
                )
            )

        return notifications

    def _seed_rapports(
        self,
        *,
        admin_user: User,
        medecins: list[Medecin],
        patients: list[Patient],
        rdvs: list[RendezVous],
        paiements: list[Paiement],
    ) -> list[RapportGenere]:
        rapports = []
        today = timezone.localdate()
        payloads = [
            (
                "Vue globale de l'activite",
                RapportGenere.TypeRapport.ACTIVITE_GLOBALE,
                today - timedelta(days=90),
                today,
                dedent(
                    f"""
                    Rapport seed activite globale
                    Patients actifs: {len(patients)}
                    Medecins actifs: {len(medecins)}
                    Rendez-vous: {len(rdvs)}
                    Paiements: {len(paiements)}
                    """
                ).strip(),
            ),
            (
                "Synthese operationnelle des rendez-vous",
                RapportGenere.TypeRapport.RENDEZ_VOUS,
                today - timedelta(days=60),
                today,
                dedent(
                    f"""
                    Rapport seed rendez-vous
                    Termines: {sum(1 for rdv in rdvs if rdv.statut_rdv == RendezVous.StatutRdv.TERMINE)}
                    Confirmes: {sum(1 for rdv in rdvs if rdv.statut_rdv == RendezVous.StatutRdv.CONFIRME)}
                    En attente: {sum(1 for rdv in rdvs if rdv.statut_rdv == RendezVous.StatutRdv.EN_ATTENTE)}
                    """
                ).strip(),
            ),
            (
                "Journal consolide des paiements",
                RapportGenere.TypeRapport.PAIEMENTS,
                today - timedelta(days=180),
                today,
                dedent(
                    f"""
                    Rapport seed paiements
                    Confirmes: {sum(1 for paiement in paiements if paiement.statut_paiement == Paiement.StatutPaiement.CONFIRME)}
                    Echoues: {sum(1 for paiement in paiements if paiement.statut_paiement == Paiement.StatutPaiement.ECHOUE)}
                    Rembourses: {sum(1 for paiement in paiements if paiement.statut_paiement == Paiement.StatutPaiement.REMBOURSE)}
                    """
                ).strip(),
            ),
            (
                "Performance des medecins",
                RapportGenere.TypeRapport.MEDECINS,
                today - timedelta(days=90),
                today,
                "Rapport seed medecins: activite, disponibilites, consultations et conversions de paiement.",
            ),
            (
                "Evolution des patients",
                RapportGenere.TypeRapport.PATIENTS,
                today - timedelta(days=120),
                today,
                "Rapport seed patients: croissance, dossiers, consultations, observations et retours de suivi.",
            ),
        ]

        for index, (titre, type_rapport, periode_debut, periode_fin, body) in enumerate(payloads, start=1):
            rapport, _ = RapportGenere.objects.update_or_create(
                titre=titre,
                type_rapport=type_rapport,
                periode_debut=periode_debut,
                periode_fin=periode_fin,
                defaults={"genere_par": admin_user},
            )
            filename = REPORTS_DIR / f"seed_{index}_{self._slugify_name(type_rapport)}.txt"
            filename.write_text(body + "\n", encoding="utf-8")
            relative_path = filename.relative_to(settings.MEDIA_ROOT)
            rapport.fichier.name = str(relative_path)
            rapport.genere_par = admin_user
            rapport.save()
            rapports.append(rapport)

        return rapports

    def _seed_configuration_djomy(self) -> None:
        ConfigurationDjomy.objects.update_or_create(
            actif=True,
            defaults={
                "cle_api": settings.DJOMY_API_KEY or "seed-demo-key",
                "url_base": settings.DJOMY_BASE_URL,
                "url_webhook": "https://healthconnect.local/webhooks/djomy/",
            },
        )

    def _seed_payment_history_for_consultation(
        self,
        *,
        consultation: Consultation,
        primary_payment: Paiement,
        rng: random.Random,
    ) -> list[Paiement]:
        history = []
        rendez_vous = consultation.rendez_vous
        if not rendez_vous:
            return history

        base_amount = Decimal(primary_payment.montant)
        base_dt = primary_payment.date_paiement or self._combine_as_aware_datetime(
            rendez_vous.date_rdv,
            rendez_vous.heure_debut,
        )

        if primary_payment.statut_paiement == Paiement.StatutPaiement.CONFIRME and rng.random() < 0.78:
            attempt = Paiement.objects.create(
                consultation=consultation,
                montant=base_amount,
                devise=primary_payment.devise,
                mode_paiement=primary_payment.mode_paiement,
                statut_paiement=Paiement.StatutPaiement.INITIE,
                date_paiement=base_dt - timedelta(minutes=rng.randint(8, 90)),
                reference_djomy=f"DJH-{rng.randint(100000, 999999)}",
                webhook_payload={
                    "source": "seed",
                    "history_type": "pre_authorisation",
                    "statut_final_associe": primary_payment.statut_paiement,
                },
            )
            history.append(attempt)

        if primary_payment.statut_paiement in [Paiement.StatutPaiement.ECHOUE, Paiement.StatutPaiement.REMBOURSE] and rng.random() < 0.7:
            retry_status = (
                Paiement.StatutPaiement.CONFIRME
                if primary_payment.statut_paiement == Paiement.StatutPaiement.ECHOUE and rng.random() < 0.55
                else Paiement.StatutPaiement.ECHOUE
            )
            retry = Paiement.objects.create(
                consultation=consultation,
                montant=base_amount,
                devise=primary_payment.devise,
                mode_paiement=rng.choice([choice for choice, _ in Paiement.ModePaiement.choices]),
                statut_paiement=retry_status,
                date_paiement=base_dt + timedelta(hours=rng.randint(2, 48)) if retry_status == Paiement.StatutPaiement.CONFIRME else None,
                reference_djomy=f"DJR-{rng.randint(100000, 999999)}" if retry_status != Paiement.StatutPaiement.ECHOUE else "",
                webhook_payload={
                    "source": "seed",
                    "history_type": "retry",
                    "precedent_statut": primary_payment.statut_paiement,
                    "nouveau_statut": retry_status,
                },
            )
            history.append(retry)

        if primary_payment.statut_paiement == Paiement.StatutPaiement.CONFIRME and rng.random() < 0.24:
            fraction = Decimal(rng.choice(["0.10", "0.20", "0.30", "0.50"]))
            remboursement = Paiement.objects.create(
                consultation=consultation,
                montant=(base_amount * fraction).quantize(Decimal("0.01")),
                devise=primary_payment.devise,
                mode_paiement=primary_payment.mode_paiement,
                statut_paiement=Paiement.StatutPaiement.REMBOURSE,
                date_paiement=base_dt + timedelta(days=rng.randint(1, 12)),
                reference_djomy=f"DJB-{rng.randint(100000, 999999)}",
                webhook_payload={
                    "source": "seed",
                    "history_type": "refund",
                    "montant_source": str(base_amount),
                    "montant_rembourse": str((base_amount * fraction).quantize(Decimal('0.01'))),
                },
            )
            history.append(remboursement)

        return history

    def _attach_avatar(self, user: User, color_start: str, color_end: str) -> None:
        image_bytes = self._build_avatar_bytes(user, color_start, color_end)
        filename = f"seeded/{user.username}.png"
        user.photo.save(filename, ContentFile(image_bytes), save=False)

    def _build_avatar_bytes(self, user: User, color_start: str, color_end: str) -> bytes:
        size = 512
        image = Image.new("RGB", (size, size), color_start)
        draw = ImageDraw.Draw(image)

        for y in range(size):
            ratio = y / float(size - 1)
            color = self._blend_hex(color_start, color_end, ratio)
            draw.line([(0, y), (size, y)], fill=color)

        accent = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        accent_draw = ImageDraw.Draw(accent)
        accent_draw.ellipse((48, 56, 464, 472), fill=(255, 255, 255, 24))
        accent_draw.ellipse((96, 124, 416, 444), fill=(255, 255, 255, 34))
        accent_draw.rounded_rectangle((92, 320, 420, 448), radius=44, fill=(255, 255, 255, 46))
        accent = accent.filter(ImageFilter.GaussianBlur(radius=3))
        image = Image.alpha_composite(image.convert("RGBA"), accent)

        draw = ImageDraw.Draw(image)
        initials = self._initials(user)
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 176)
            sub_font = ImageFont.truetype("DejaVuSans.ttf", 28)
        except OSError:
            font = ImageFont.load_default()
            sub_font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), initials, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = (size - text_width) / 2
        text_y = 150
        draw.text((text_x, text_y), initials, fill="white", font=font)

        role_text = "MEDECIN" if user.role == User.Role.MEDECIN else "PATIENT"
        if user.role == User.Role.ADMIN:
            role_text = "ADMIN"
        role_bbox = draw.textbbox((0, 0), role_text, font=sub_font)
        role_width = role_bbox[2] - role_bbox[0]
        draw.text(((size - role_width) / 2, 360), role_text, fill=(255, 255, 255, 230), font=sub_font)

        output = BytesIO()
        image.convert("RGB").save(output, format="PNG", quality=95)
        return output.getvalue()

    def _blend_hex(self, start: str, end: str, ratio: float) -> tuple[int, int, int]:
        start_rgb = tuple(int(start[index:index + 2], 16) for index in (1, 3, 5))
        end_rgb = tuple(int(end[index:index + 2], 16) for index in (1, 3, 5))
        return tuple(
            round(start_channel + (end_channel - start_channel) * ratio)
            for start_channel, end_channel in zip(start_rgb, end_rgb)
        )

    def _combine_as_aware_datetime(self, day: date, clock: time) -> datetime:
        tz = timezone.get_current_timezone()
        naive = datetime.combine(day, clock)
        return timezone.make_aware(naive, tz) if timezone.is_naive(naive) else naive

    def _build_email(self, first_name: str, last_name: str, index: int) -> str:
        first_slug = self._slugify_name(first_name)
        last_slug = self._slugify_name(last_name)
        return f"{first_slug}.{last_slug}{index}@{SEED_EMAIL_DOMAIN}"

    def _build_profiles(
        self,
        *,
        count: int,
        seed_profiles: list[tuple[str, str, str]],
        rng: random.Random,
    ) -> list[tuple[str, str, str]]:
        profiles = list(seed_profiles[: min(count, len(seed_profiles))])
        seen = {(first, last) for first, last, _ in profiles}

        while len(profiles) < max(1, count):
            sexe = rng.choice(["M", "F"])
            first_name = rng.choice(PRENOMS_MASCULINS if sexe == "M" else PRENOMS_FEMININS)
            last_name = rng.choice(NOMS_FAMILLE)
            suffix = ""
            if (first_name, last_name) in seen:
                suffix = f" {rng.choice(['Alpha', 'Junior', 'I', 'II', 'III'])}"
            candidate = (f"{first_name}{suffix}", last_name, sexe)
            if (candidate[0], candidate[1]) in seen:
                continue
            seen.add((candidate[0], candidate[1]))
            profiles.append(candidate)

        return profiles

    def _slugify_name(self, value: str) -> str:
        return (
            value.lower()
            .replace(" ", "")
            .replace("'", "")
            .replace("’", "")
            .replace("é", "e")
            .replace("è", "e")
            .replace("ê", "e")
            .replace("à", "a")
            .replace("ù", "u")
        )

    def _random_birth_date(self, rng: random.Random) -> date:
        age = rng.randint(2, 78)
        extra_days = rng.randint(0, 364)
        return timezone.localdate() - timedelta(days=(age * 365) + extra_days)

    def _random_color_pair(self, rng: random.Random) -> tuple[str, str]:
        palette = [
            ("#0f766e", "#14b8a6"),
            ("#1d4ed8", "#60a5fa"),
            ("#b45309", "#f59e0b"),
            ("#be123c", "#fb7185"),
            ("#4f46e5", "#818cf8"),
            ("#166534", "#4ade80"),
            ("#7c2d12", "#fb923c"),
            ("#334155", "#94a3b8"),
        ]
        return rng.choice(palette)

    def _initials(self, user: User) -> str:
        first = (user.first_name[:1] or "").upper()
        last = (user.last_name[:1] or "").upper()
        return f"{first}{last}" or "HC"
