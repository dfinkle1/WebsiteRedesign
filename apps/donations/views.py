import json
import logging

from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django_ratelimit.decorators import ratelimit

from .forms import DonationForm
from .models import Donation
from .services.paypal import capture_order, create_order, verify_webhook_signature
from .services.webhooks import handle_webhook

logger = logging.getLogger(__name__)


@ratelimit(key="ip", rate="10/h", method="POST", block=True)
def donate_view(request):
    if request.method == "POST":
        form = DonationForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            donation = Donation.objects.create(
                donor_name=data["donor_name"],
                donor_email=data["donor_email"],
                amount=data["amount"],
                category=data["category"],
                ip_address=_get_client_ip(request),
            )

            try:
                result = create_order(donation)
            except Exception:
                logger.exception("PayPal create_order failed for donation %s", donation.pk)
                donation.status = Donation.Status.FAILED
                donation.save(update_fields=["status"])
                messages.error(request, "We couldn't connect to PayPal right now. Please try again.")
                return render(request, "donations/form.html", {"form": form})

            donation.paypal_order_id = result["order_id"]
            donation.save(update_fields=["paypal_order_id"])

            return HttpResponseRedirect(result["approve_url"])
    else:
        form = DonationForm()

    return render(request, "donations/form.html", {"form": form})


def paypal_return_view(request):
    """
    PayPal redirects here after the donor approves payment.
    PayPal appends ?token=<order_id>&PayerID=<payer_id> to the URL.

    We attempt to capture here for fast UX, but the webhook is the
    authoritative source of truth. Both paths are idempotent.
    """
    order_id = request.GET.get("token")
    if not order_id:
        return render(request, "donations/cancel.html")

    try:
        donation = Donation.objects.get(paypal_order_id=order_id)
    except Donation.DoesNotExist:
        logger.error("No donation found for PayPal order_id=%s on return", order_id)
        return render(request, "donations/cancel.html")

    # Only attempt capture if still pending — webhook may have already handled it
    if donation.status == Donation.Status.PENDING:
        try:
            capture_order(order_id)
            # Don't update the DB here — the webhook does that authoritatively
        except Exception:
            logger.exception("Capture failed for order_id=%s on return", order_id)

    return render(request, "donations/success.html", {"donation": donation})


def paypal_cancel_view(request):
    """Donor clicked Cancel on the PayPal page."""
    order_id = request.GET.get("token")
    if order_id:
        Donation.objects.filter(
            paypal_order_id=order_id,
            status=Donation.Status.PENDING,
        ).update(status=Donation.Status.CANCELLED)

    return render(request, "donations/cancel.html")


@method_decorator(csrf_exempt, name="dispatch")
class PayPalWebhookView(View):
    """
    Receives PayPal webhook events.

    CSRF exempt because PayPal can't provide a CSRF token.
    Security is provided by verify_webhook_signature() instead —
    that call is mandatory and must never be removed.
    """

    def post(self, request):
        raw_body = request.body

        if not verify_webhook_signature(request.headers, raw_body):
            logger.warning("PayPal webhook signature verification failed — rejected")
            return HttpResponse(status=400)

        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            return HttpResponse(status=400)

        event_id = payload.get("id", "")
        event_type = payload.get("event_type", "")

        try:
            handle_webhook(
                event_type=event_type,
                event_data=payload,
                raw_body=raw_body,
                paypal_event_id=event_id,
            )
        except Exception:
            # Return 500 so PayPal retries — handler already logged the error
            return HttpResponse(status=500)

        return HttpResponse(status=200)


def _get_client_ip(request) -> str:
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")
