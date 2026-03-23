"""
PayPal Orders v2 API integration.

Required env vars (set in .env):
    PAYPAL_CLIENT_ID
    PAYPAL_CLIENT_SECRET
    PAYPAL_WEBHOOK_ID   — from the PayPal developer dashboard webhook configuration
    PAYPAL_MODE         — "sandbox" or "live"
    SITE_URL            — e.g. https://aimath.org (used to build return/cancel URLs)
"""
import json
import logging
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

_SANDBOX_BASE = "https://api-m.sandbox.paypal.com"
_LIVE_BASE = "https://api-m.paypal.com"


def _base_url() -> str:
    mode = getattr(settings, "PAYPAL_MODE", "sandbox")
    return _SANDBOX_BASE if mode == "sandbox" else _LIVE_BASE


# ---------------------------------------------------------------------------
# Access token — cached in memory for up to 8 hours (PayPal tokens last 9h)
# ---------------------------------------------------------------------------
_token_cache: dict = {"token": None, "expires_at": 0}


def _get_access_token() -> str:
    if _token_cache["token"] and time.time() < _token_cache["expires_at"]:
        return _token_cache["token"]

    response = requests.post(
        f"{_base_url()}/v1/oauth2/token",
        auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET),
        data={"grant_type": "client_credentials"},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = time.time() + data["expires_in"] - 60  # 1-min safety buffer

    return _token_cache["token"]


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {_get_access_token()}",
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# Create order
# ---------------------------------------------------------------------------
def create_order(donation) -> dict:
    """
    Creates a PayPal order for the given Donation instance.

    Returns:
        {"order_id": "...", "approve_url": "https://www.paypal.com/checkoutnow?token=..."}

    Raises:
        requests.HTTPError on PayPal API failure.
    """
    site_url = getattr(settings, "SITE_URL", "http://localhost:8000").rstrip("/")

    payload = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                # custom_id is how we find this donation from the webhook,
                # even if the user closes their browser before returning.
                "custom_id": str(donation.pk),
                "description": f"Donation to {donation.category.name}",
                "amount": {
                    "currency_code": donation.currency,
                    "value": str(donation.amount),
                },
            }
        ],
        "application_context": {
            "return_url": f"{site_url}/donate/paypal/return/",
            "cancel_url": f"{site_url}/donate/paypal/cancel/",
            "brand_name": "American Institute of Mathematics",
            "user_action": "PAY_NOW",
            "shipping_preference": "NO_SHIPPING",
        },
    }

    response = requests.post(
        f"{_base_url()}/v2/checkout/orders",
        headers=_headers(),
        json=payload,
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    approve_url = next(link["href"] for link in data["links"] if link["rel"] == "approve")

    return {"order_id": data["id"], "approve_url": approve_url}


# ---------------------------------------------------------------------------
# Capture order (called on return URL)
# ---------------------------------------------------------------------------
def capture_order(order_id: str) -> dict:
    """
    Captures an approved PayPal order. Returns the full capture response.
    Raises requests.HTTPError on failure.
    """
    response = requests.post(
        f"{_base_url()}/v2/checkout/orders/{order_id}/capture",
        headers=_headers(),
        json={},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------------------------
# Refund a capture
# ---------------------------------------------------------------------------
def refund_capture(capture_id: str) -> dict:
    """
    Issues a full refund for the given PayPal capture ID.

    Returns the PayPal refund response dict.
    Raises requests.HTTPError on failure.
    """
    response = requests.post(
        f"{_base_url()}/v2/payments/captures/{capture_id}/refund",
        headers=_headers(),
        json={},  # empty body = full refund
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------------------------
# Webhook signature verification
# ---------------------------------------------------------------------------
def verify_webhook_signature(request_headers: dict, raw_body: bytes) -> bool:
    """
    Calls PayPal's verify-webhook-signature endpoint to confirm the webhook
    actually came from PayPal.

    IMPORTANT: Never skip this. An attacker could POST a fake
    PAYMENT.CAPTURE.COMPLETED to fraudulently trigger receipt emails
    and mark donations as paid without any money changing hands.
    """
    payload = {
        "auth_algo": request_headers.get("PAYPAL-AUTH-ALGO"),
        "cert_url": request_headers.get("PAYPAL-CERT-URL"),
        "transmission_id": request_headers.get("PAYPAL-TRANSMISSION-ID"),
        "transmission_sig": request_headers.get("PAYPAL-TRANSMISSION-SIG"),
        "transmission_time": request_headers.get("PAYPAL-TRANSMISSION-TIME"),
        "webhook_id": settings.PAYPAL_WEBHOOK_ID,
        "webhook_event": json.loads(raw_body),
    }

    try:
        response = requests.post(
            f"{_base_url()}/v1/notifications/verify-webhook-signature",
            headers=_headers(),
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        return response.json().get("verification_status") == "SUCCESS"
    except Exception:
        logger.exception("PayPal webhook verification request failed")
        return False
