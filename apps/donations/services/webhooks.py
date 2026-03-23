import logging

from django.db import transaction
from django.utils import timezone

from apps.donations.models import Donation, WebhookEvent
from apps.donations.services.emails import send_receipt_email
from apps.donations.services.receipts import generate_receipt_number

logger = logging.getLogger(__name__)


def handle_webhook(event_type: str, event_data: dict, raw_body: bytes, paypal_event_id: str) -> None:
    """
    Entry point for all incoming PayPal webhook events.
    Every event is logged to WebhookEvent before processing.
    """
    # Idempotency: if we've seen this event ID before, skip it.
    # PayPal will occasionally deliver the same webhook more than once.
    event, created = WebhookEvent.objects.get_or_create(
        paypal_event_id=paypal_event_id,
        defaults={
            "event_type": event_type,
            "raw_body": raw_body.decode("utf-8"),
        },
    )

    if not created:
        logger.info("Duplicate webhook %s ignored", paypal_event_id)
        return

    try:
        if event_type == "PAYMENT.CAPTURE.COMPLETED":
            _handle_capture_completed(event_data)
        elif event_type == "PAYMENT.CAPTURE.DENIED":
            _handle_capture_denied(event_data)
        else:
            logger.info("Unhandled webhook event type: %s", event_type)

        event.processed = True
        event.save(update_fields=["processed"])

    except Exception as exc:
        # Save the error so staff can debug from admin, then re-raise
        # so the view returns 500 and PayPal retries delivery.
        event.error = str(exc)
        event.save(update_fields=["error"])
        logger.exception("Error processing webhook %s", paypal_event_id)
        raise


def _handle_capture_completed(event_data: dict) -> None:
    """
    Marks the donation completed and sends the receipt email.

    PayPal places our custom_id (donation.pk) at:
        event_data["resource"]["purchase_units"][0]["custom_id"]

    The capture ID is at:
        event_data["resource"]["id"]
    """
    resource = event_data.get("resource", {})
    capture_id = resource.get("id", "")

    # custom_id is the most reliable lookup — it's what we set on order creation
    purchase_units = resource.get("purchase_units", [])
    custom_id = purchase_units[0].get("custom_id") if purchase_units else None

    # Fallback: look up by PayPal order ID
    order_id = (
        resource.get("supplementary_data", {})
        .get("related_ids", {})
        .get("order_id")
    )

    donation = None
    if custom_id:
        try:
            donation = Donation.objects.get(pk=custom_id)
        except (Donation.DoesNotExist, ValueError):
            logger.error("Donation not found for custom_id=%s", custom_id)

    if donation is None and order_id:
        try:
            donation = Donation.objects.get(paypal_order_id=order_id)
        except Donation.DoesNotExist:
            logger.error("Donation not found for order_id=%s", order_id)

    if donation is None:
        logger.error("Could not resolve donation from webhook payload: %s", event_data)
        return

    # Idempotent: already completed means receipt was already sent
    if donation.status == Donation.Status.COMPLETED:
        logger.info("Donation %s already completed — skipping", donation.pk)
        return

    with transaction.atomic():
        receipt_number = generate_receipt_number(donation)
        Donation.objects.filter(pk=donation.pk).update(
            status=Donation.Status.COMPLETED,
            paypal_capture_id=capture_id,
            receipt_number=receipt_number,
            completed_at=timezone.now(),
        )
        donation.refresh_from_db()

    send_receipt_email(donation)
    logger.info("Donation %s completed. Receipt %s sent to %s.", donation.pk, receipt_number, donation.donor_email)


def _handle_capture_denied(event_data: dict) -> None:
    resource = event_data.get("resource", {})
    order_id = (
        resource.get("supplementary_data", {})
        .get("related_ids", {})
        .get("order_id")
    )
    if order_id:
        updated = Donation.objects.filter(
            paypal_order_id=order_id,
            status=Donation.Status.PENDING,
        ).update(status=Donation.Status.FAILED)
        if updated:
            logger.info("Donation with order_id=%s marked failed", order_id)
