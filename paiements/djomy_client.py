import hashlib
import hmac
import json

import requests
from django.conf import settings


class DjomyClient:
    """Client pour l'API de paiement Djomy (https://developers.djomy.africa/)."""

    def __init__(self):
        self.api_key = settings.DJOMY_API_KEY
        self.base_url = settings.DJOMY_BASE_URL.rstrip('/')
        self.webhook_secret = settings.DJOMY_WEBHOOK_SECRET

    def _headers(self):
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

    def initier_paiement(self, montant, telephone, reference, description=''):
        """
        Initie un paiement mobile money via Djomy.

        Args:
            montant (Decimal|float): Montant à payer.
            telephone (str): Numéro de téléphone du payeur (format international).
            reference (str): Référence interne unique (ex: PAY-XXXXXXXX).
            description (str): Libellé de la transaction.

        Returns:
            dict: Réponse de l'API Djomy.
        """
        payload = {
            'amount': float(montant),
            'phone': telephone,
            'reference': reference,
            'description': description,
            'currency': 'GNF',
        }
        response = requests.post(
            f'{self.base_url}/payments/initiate',
            headers=self._headers(),
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def verifier_statut(self, reference_djomy):
        """
        Vérifie le statut d'une transaction via son ID Djomy.

        Args:
            reference_djomy (str): ID de transaction retourné par Djomy.

        Returns:
            dict: Réponse de l'API Djomy.
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
        Valide et traite un webhook entrant de Djomy.

        Args:
            payload (bytes): Corps brut de la requête HTTP.
            signature (str): Valeur de l'en-tête X-Djomy-Signature.

        Returns:
            dict: Données du webhook décodées si la signature est valide.

        Raises:
            ValueError: Si la signature HMAC est invalide.
        """
        expected = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected, signature):
            raise ValueError('Signature webhook invalide.')

        return json.loads(payload)
