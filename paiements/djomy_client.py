# ==============================================================================
# paiements/djomy_client.py — Client HTTP pour l'API Djomy
# ==============================================================================
# Djomy est l'agrégateur de paiement mobile money guinéen (djomy.africa).
# Il unifie Orange Money, MTN Money et Wave sous une seule API REST.
#
# Ce fichier implémente le patron "Client HTTP" :
#   - DjomyClient encapsule toutes les requêtes vers l'API externe
#   - Les vues ne font qu'instancier DjomyClient() et appeler ses méthodes
#   - La sécurité webhook repose sur HMAC-SHA256 (algorithme de signature)
#
# NOTE : Dans l'environnement de démonstration actuel, DjomyClient N'EST PAS
# appelé (PayerRDVView simule directement la confirmation). Ce fichier décrit
# l'intégration réelle prévue pour la production.
# ==============================================================================

import hashlib
import hmac
import json

import requests
from django.conf import settings


class DjomyClient:
    """
    Client pour l'API de paiement Djomy (https://developers.djomy.africa/).

    Toutes les requêtes sortantes sont authentifiées par un Bearer Token
    (clé API). Toutes les requêtes entrantes (webhooks) sont vérifiées
    par une signature HMAC-SHA256.
    """

    def __init__(self):
        # Lus depuis settings → eux-mêmes lus depuis .env via django-environ
        # Ne jamais coder ces valeurs en dur dans le code source !
        self.api_key        = settings.DJOMY_API_KEY
        self.base_url       = settings.DJOMY_BASE_URL.rstrip('/')
        self.webhook_secret = settings.DJOMY_WEBHOOK_SECRET

    def _headers(self):
        """
        Construit les en-têtes HTTP communs à toutes les requêtes sortantes.

        Bearer Token : l'API Djomy utilise OAuth2 Bearer pour l'authentification.
        Le serveur Djomy vérifie que le token correspond à un compte actif.
        """
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

    def initier_paiement(self, montant, telephone, reference, description=''):
        """
        Initie un paiement mobile money via Djomy.

        En pratique, Djomy envoie une notification USSD sur le téléphone
        de l'utilisateur qui doit confirmer avec son code PIN mobile money.

        Args:
            montant (Decimal|float): Montant à payer en GNF.
            telephone (str): Numéro international du payeur (ex : +224622000000).
            reference (str): Référence interne unique HealthConnect (PAY-XXXXXXXXXX).
            description (str): Libellé affiché à l'utilisateur sur son téléphone.

        Returns:
            dict: Réponse JSON de l'API Djomy (contient transaction_id, status…).

        Raises:
            requests.HTTPError: Si l'API retourne un code d'erreur HTTP.
        """
        payload = {
            'amount':      float(montant),
            'phone':       telephone,
            'reference':   reference,
            'description': description,
            'currency':    'GNF',
        }
        response = requests.post(
            f'{self.base_url}/payments/initiate',
            headers=self._headers(),
            json=payload,
            timeout=30,  # 30 secondes max — au-delà, lever une exception
        )
        response.raise_for_status()  # lève HTTPError si status >= 400
        return response.json()

    def verifier_statut(self, reference_djomy):
        """
        Vérifie le statut d'une transaction via son ID Djomy.

        Utilisé en complément des webhooks : si un webhook n'est jamais reçu
        (coupure réseau, délai), on peut interroger l'API directement.

        Args:
            reference_djomy (str): ID de transaction retourné par Djomy.

        Returns:
            dict: Réponse JSON avec le statut actuel ('success', 'pending', 'failed').
        """
        response = requests.get(
            f'{self.base_url}/payments/{reference_djomy}',
            headers=self._headers(),
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def traiter_webhook(self, payload, signature):
        """
        Valide et décode un webhook entrant de Djomy.

        PRINCIPE DE SÉCURITÉ HMAC-SHA256 :
          Djomy signe chaque webhook en calculant HMAC(secret, corps_brut, sha256).
          Notre serveur recalcule la même signature et compare avec celle reçue.
          Si elles correspondent, le webhook est authentique (vient bien de Djomy).
          Si elles diffèrent, quelqu'un a forgé la requête → on rejette.

          hmac.compare_digest() est résistant aux "timing attacks" : il compare
          toujours les deux chaînes en temps constant, même si elles diffèrent
          dès le premier caractère, pour éviter de révéler des informations par
          le temps de réponse.

        Args:
            payload (bytes): Corps brut de la requête HTTP (avant décodage JSON).
            signature (str): Valeur de l'en-tête X-Djomy-Signature.

        Returns:
            dict: Données du webhook (transaction_id, status, reference…).

        Raises:
            ValueError: Si la signature HMAC est invalide (requête falsifiée).
        """
        # On calcule la signature attendue avec notre secret partagé
        expected = hmac.new(
            self.webhook_secret.encode(),  # secret en bytes
            payload,                        # corps brut en bytes
            hashlib.sha256,                 # algorithme de hachage
        ).hexdigest()  # représentation hexadécimale du HMAC

        # Comparaison en temps constant (sécurité anti-timing attack)
        if not hmac.compare_digest(expected, signature):
            raise ValueError('Signature webhook invalide.')

        # Signature valide → on peut décoder le JSON en toute confiance
        return json.loads(payload)
