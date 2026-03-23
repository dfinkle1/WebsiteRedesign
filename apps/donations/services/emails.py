import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from apps.donations.models import OrganizationSettings

logger = logging.getLogger(__name__)


def send_receipt_email(donation) -> bool:
    """
    Sends a tax-compliant donation receipt to the donor.

    Called ONLY after PAYMENT.CAPTURE.COMPLETED webhook is verified.
    Returns True on success, False on failure.
    """
    org = OrganizationSettings.get()

    context = {
        "donation": donation,
        "org": org,
        "tax_deductible": not donation.goods_or_services_provided,
    }

    subject = f"Thank you for your donation — Receipt {donation.receipt_number}"
    from_email = getattr(settings, "DONATION_RECEIPT_FROM_EMAIL", settings.DEFAULT_FROM_EMAIL)

    text_body = render_to_string("donations/emails/receipt.txt", context)
    html_body = render_to_string("donations/emails/receipt.html", context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=from_email,
        to=[donation.donor_email],
        reply_to=[from_email],
    )
    msg.attach_alternative(html_body, "text/html")

    try:
        msg.send()
        donation.receipt_sent_at = timezone.now()
        donation.save(update_fields=["receipt_sent_at"])
        logger.info("Receipt email sent for donation %s to %s", donation.pk, donation.donor_email)
        return True
    except Exception:
        logger.exception("Failed to send receipt email for donation %s", donation.pk)
        return False
