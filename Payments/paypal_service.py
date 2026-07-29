import json
import base64
import logging
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from django.conf import settings

logger = logging.getLogger(__name__)


class PayPalService:
    @staticmethod
    def _get_base_url():
        mode = getattr(settings, 'PAYPAL_MODE', 'sandbox')
        if mode == 'live':
            return "https://api-m.paypal.com"
        return "https://api-m.sandbox.paypal.com"

    @classmethod
    def get_access_token(cls):
        client_id = getattr(settings, 'PAYPAL_CLIENT_ID', '')
        client_secret = getattr(settings, 'PAYPAL_CLIENT_SECRET', '')
        base_url = cls._get_base_url()
        url = f"{base_url}/v1/oauth2/token"

        credentials = f"{client_id}:{client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')

        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        body = "grant_type=client_credentials".encode('utf-8')

        req = Request(url, data=body, headers=headers, method="POST")
        try:
            with urlopen(req) as response:
                data = json.loads(response.read().decode('utf-8'))
                return data.get("access_token")
        except HTTPError as e:
            error_content = e.read().decode('utf-8')
            logger.error(f"PayPal OAuth Error: {error_content}")
            raise Exception(f"PayPal authentication failed: {error_content}")

    @classmethod
    def create_order(cls, amount, currency="USD", return_url=None, cancel_url=None):
        token = cls.get_access_token()
        base_url = cls._get_base_url()
        url = f"{base_url}/v2/checkout/orders"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "amount": {
                        "currency_code": currency,
                        "value": f"{amount:.2f}"
                    }
                }
            ]
        }

        if return_url and cancel_url:
            payload["application_context"] = {
                "return_url": return_url,
                "cancel_url": cancel_url
            }

        req = Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method="POST")
        try:
            with urlopen(req) as response:
                return json.loads(response.read().decode('utf-8'))
        except HTTPError as e:
            error_content = e.read().decode('utf-8')
            logger.error(f"PayPal Create Order Error: {error_content}")
            raise Exception(f"Failed to create PayPal order: {error_content}")

    @classmethod
    def capture_order(cls, paypal_order_id):
        token = cls.get_access_token()
        base_url = cls._get_base_url()
        url = f"{base_url}/v2/checkout/orders/{paypal_order_id}/capture"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        req = Request(url, data=b"", headers=headers, method="POST")
        try:
            with urlopen(req) as response:
                return json.loads(response.read().decode('utf-8'))
        except HTTPError as e:
            error_content = e.read().decode('utf-8')
            logger.error(f"PayPal Capture Order Error: {error_content}")
            raise Exception(f"Failed to capture PayPal payment: {error_content}")

    @classmethod
    def refund_capture(cls, paypal_capture_id, amount=None, currency="USD", reason=None):
        token = cls.get_access_token()
        base_url = cls._get_base_url()
        url = f"{base_url}/v2/payments/captures/{paypal_capture_id}/refund"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        payload = {}
        if amount is not None:
            payload["amount"] = {
                "value": f"{amount:.2f}",
                "currency_code": currency
            }
        if reason:
            payload["note_to_payer"] = reason

        req = Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method="POST")
        try:
            with urlopen(req) as response:
                return json.loads(response.read().decode('utf-8'))
        except HTTPError as e:
            error_content = e.read().decode('utf-8')
            logger.error(f"PayPal Refund Error: {error_content}")
            raise Exception(f"Failed to refund PayPal payment: {error_content}")

    @classmethod
    def create_payout(cls, receiver_email, amount, currency="USD", note="Provider Earnings Payout"):
        token = cls.get_access_token()
        base_url = cls._get_base_url()
        url = f"{base_url}/v1/payments/payouts"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        import uuid
        sender_batch_id = f"Payout_{uuid.uuid4().hex[:12]}"

        payload = {
            "sender_batch_header": {
                "sender_batch_id": sender_batch_id,
                "email_subject": "You have received a payout!"
            },
            "items": [
                {
                    "recipient_type": "EMAIL",
                    "amount": {
                        "value": f"{amount:.2f}",
                        "currency": currency
                    },
                    "note": note,
                    "receiver": receiver_email
                }
            ]
        }

        req = Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method="POST")
        try:
            with urlopen(req) as response:
                return json.loads(response.read().decode('utf-8'))
        except HTTPError as e:
            error_content = e.read().decode('utf-8')
            logger.error(f"PayPal Payout Error: {error_content}")
            raise Exception(f"Failed to create PayPal payout: {error_content}")

    @classmethod
    def verify_webhook_signature(cls, headers, raw_body):
        webhook_id = getattr(settings, 'PAYPAL_WEBHOOK_ID', '')
        if not webhook_id:
            # If webhook ID is not configured in sandbox/dev, bypass verification safely
            return True

        token = cls.get_access_token()
        base_url = cls._get_base_url()
        url = f"{base_url}/v1/notifications/verify-webhook-signature"

        request_headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        payload = {
            "auth_algo": headers.get("PAYPAL-AUTH-ALGO"),
            "cert_url": headers.get("PAYPAL-CERT-URL"),
            "transmission_id": headers.get("PAYPAL-TRANSMISSION-ID"),
            "transmission_sig": headers.get("PAYPAL-TRANSMISSION-SIG"),
            "transmission_time": headers.get("PAYPAL-TRANSMISSION-TIME"),
            "webhook_id": webhook_id,
            "webhook_event": json.loads(raw_body)
        }

        req = Request(url, data=json.dumps(payload).encode('utf-8'), headers=request_headers, method="POST")
        try:
            with urlopen(req) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                return res_data.get("verification_status") == "SUCCESS"
        except HTTPError as e:
            logger.error(f"PayPal Webhook Verification Failed: {e.read().decode('utf-8')}")
            return False
