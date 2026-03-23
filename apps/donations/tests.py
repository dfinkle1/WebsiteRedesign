import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.utils import timezone

from .admin import DonationAdmin
from .models import Donation, DonationCategory, OrganizationSettings, WebhookEvent
from .forms import DonationForm
from .services.receipts import generate_receipt_number
from .services.webhooks import handle_webhook

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_category(**kwargs):
    defaults = {"name": "General Fund", "slug": "general", "is_active": True}
    defaults.update(kwargs)
    return DonationCategory.objects.create(**defaults)


def make_donation(category=None, **kwargs):
    if category is None:
        category = make_category()
    defaults = {
        "donor_name": "Jane Smith",
        "donor_email": "jane@example.com",
        "amount": Decimal("100.00"),
        "category": category,
        "status": Donation.Status.PENDING,
        "paypal_order_id": "ORDER-123",
    }
    defaults.update(kwargs)
    return Donation.objects.create(**defaults)


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class DonationModelTests(TestCase):

    def setUp(self):
        self.category = make_category()

    def test_str(self):
        d = make_donation(self.category)
        self.assertIn("Jane Smith", str(d))
        self.assertIn("100.00", str(d))

    def test_is_tax_deductible_default(self):
        d = make_donation(self.category)
        self.assertTrue(d.is_tax_deductible)

    def test_is_tax_deductible_false_when_goods_provided(self):
        d = make_donation(self.category, goods_or_services_provided=True)
        self.assertFalse(d.is_tax_deductible)

    def test_default_status_is_pending(self):
        d = make_donation(self.category)
        self.assertEqual(d.status, Donation.Status.PENDING)

    def test_default_currency_is_usd(self):
        d = make_donation(self.category)
        self.assertEqual(d.currency, "USD")


class OrganizationSettingsTests(TestCase):

    def test_get_creates_singleton(self):
        self.assertEqual(OrganizationSettings.objects.count(), 0)
        org = OrganizationSettings.get()
        self.assertEqual(OrganizationSettings.objects.count(), 1)
        self.assertEqual(org.legal_name, "American Institute of Mathematics")

    def test_get_returns_existing_row(self):
        OrganizationSettings.get()
        OrganizationSettings.get()
        self.assertEqual(OrganizationSettings.objects.count(), 1)


class DonationCategoryTests(TestCase):

    def test_str(self):
        cat = make_category(name="Workshops", slug="workshops")
        self.assertEqual(str(cat), "Workshops")

    def test_inactive_category_not_in_active_queryset(self):
        make_category(name="Active", slug="active", is_active=True)
        make_category(name="Inactive", slug="inactive", is_active=False)
        active = DonationCategory.objects.filter(is_active=True)
        self.assertEqual(active.count(), 1)
        self.assertEqual(active.first().name, "Active")


# ---------------------------------------------------------------------------
# Form tests
# ---------------------------------------------------------------------------

class DonationFormTests(TestCase):

    def setUp(self):
        self.category = make_category()

    def _valid_data(self, **overrides):
        data = {
            "donor_name": "Jane Smith",
            "donor_email": "jane@example.com",
            "amount": "100.00",
            "category": self.category.pk,
        }
        data.update(overrides)
        return data

    def test_valid_form(self):
        form = DonationForm(data=self._valid_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_name(self):
        form = DonationForm(data=self._valid_data(donor_name=""))
        self.assertFalse(form.is_valid())
        self.assertIn("Please enter your full name", form.errors["donor_name"][0])

    def test_missing_email(self):
        form = DonationForm(data=self._valid_data(donor_email=""))
        self.assertFalse(form.is_valid())
        self.assertIn("Please enter your email address", form.errors["donor_email"][0])

    def test_invalid_email(self):
        form = DonationForm(data=self._valid_data(donor_email="not-an-email"))
        self.assertFalse(form.is_valid())
        self.assertIn("valid email", form.errors["donor_email"][0])

    def test_missing_amount(self):
        form = DonationForm(data=self._valid_data(amount=""))
        self.assertFalse(form.is_valid())
        self.assertIn("Please enter a donation amount", form.errors["amount"][0])

    def test_amount_below_minimum(self):
        form = DonationForm(data=self._valid_data(amount="0.50"))
        self.assertFalse(form.is_valid())
        self.assertIn("Minimum donation", form.errors["amount"][0])

    def test_amount_above_maximum(self):
        form = DonationForm(data=self._valid_data(amount="100001"))
        self.assertFalse(form.is_valid())
        self.assertIn("$100,000", form.errors["amount"][0])

    def test_missing_category(self):
        form = DonationForm(data=self._valid_data(category=""))
        self.assertFalse(form.is_valid())
        self.assertIn("Please select a fund", form.errors["category"][0])

    def test_inactive_category_rejected(self):
        inactive = make_category(name="Old Fund", slug="old", is_active=False)
        form = DonationForm(data=self._valid_data(category=inactive.pk))
        self.assertFalse(form.is_valid())

    def test_is_invalid_class_added_to_errored_fields(self):
        """Bound form with errors should add is-invalid CSS class to failing widgets."""
        form = DonationForm(data=self._valid_data(donor_name="", amount=""))
        form.is_valid()
        self.assertIn("is-invalid", form.fields["donor_name"].widget.attrs["class"])
        self.assertIn("is-invalid", form.fields["amount"].widget.attrs["class"])
        # Valid fields should not get is-invalid
        self.assertNotIn("is-invalid", form.fields["donor_email"].widget.attrs.get("class", ""))


# ---------------------------------------------------------------------------
# Receipt number tests
# ---------------------------------------------------------------------------

class ReceiptNumberTests(TestCase):

    def setUp(self):
        self.category = make_category()

    def test_format(self):
        d = make_donation(self.category)
        number = generate_receipt_number(d)
        year = timezone.now().year
        self.assertTrue(number.startswith(f"AIM-{year}-"))
        self.assertEqual(len(number.split("-")[-1]), 5)  # zero-padded 5 digits

    def test_sequential(self):
        cat = self.category
        d1 = make_donation(cat, receipt_number=None)
        d2 = make_donation(cat, receipt_number=None, paypal_order_id="ORDER-456")

        n1 = generate_receipt_number(d1)
        d1.receipt_number = n1
        d1.save()

        n2 = generate_receipt_number(d2)

        # Second number should be one higher
        seq1 = int(n1.split("-")[-1])
        seq2 = int(n2.split("-")[-1])
        self.assertEqual(seq2, seq1 + 1)

    def test_unique_across_donations(self):
        donations = [make_donation(self.category, paypal_order_id=f"ORDER-{i}") for i in range(5)]
        numbers = set()
        for d in donations:
            n = generate_receipt_number(d)
            d.receipt_number = n
            d.save()
            numbers.add(n)
        self.assertEqual(len(numbers), 5)


# ---------------------------------------------------------------------------
# Webhook handler tests
# ---------------------------------------------------------------------------

class WebhookHandlerTests(TestCase):

    def setUp(self):
        self.category = make_category()
        self.donation = make_donation(
            self.category,
            paypal_order_id="ORDER-ABC",
            status=Donation.Status.PENDING,
        )

    def _capture_event(self, custom_id=None, order_id=None, capture_id="CAP-999"):
        resource = {
            "id": capture_id,
            "purchase_units": [{"custom_id": str(custom_id or self.donation.pk)}],
            "supplementary_data": {"related_ids": {"order_id": order_id or "ORDER-ABC"}},
        }
        return {
            "id": "EVT-001",
            "event_type": "PAYMENT.CAPTURE.COMPLETED",
            "resource": resource,
        }

    @patch("apps.donations.services.webhooks.send_receipt_email")
    def test_capture_completed_marks_donation_completed(self, mock_email):
        mock_email.return_value = True
        event = self._capture_event()

        handle_webhook(
            event_type="PAYMENT.CAPTURE.COMPLETED",
            event_data=event,
            raw_body=json.dumps(event).encode(),
            paypal_event_id="EVT-001",
        )

        self.donation.refresh_from_db()
        self.assertEqual(self.donation.status, Donation.Status.COMPLETED)
        self.assertIsNotNone(self.donation.receipt_number)
        self.assertIsNotNone(self.donation.completed_at)
        self.assertEqual(self.donation.paypal_capture_id, "CAP-999")

    @patch("apps.donations.services.webhooks.send_receipt_email")
    def test_capture_completed_sends_receipt(self, mock_email):
        mock_email.return_value = True
        event = self._capture_event()

        handle_webhook(
            event_type="PAYMENT.CAPTURE.COMPLETED",
            event_data=event,
            raw_body=json.dumps(event).encode(),
            paypal_event_id="EVT-001",
        )

        mock_email.assert_called_once()

    @patch("apps.donations.services.webhooks.send_receipt_email")
    def test_duplicate_webhook_is_ignored(self, mock_email):
        mock_email.return_value = True
        event = self._capture_event()
        raw = json.dumps(event).encode()

        handle_webhook("PAYMENT.CAPTURE.COMPLETED", event, raw, "EVT-001")
        handle_webhook("PAYMENT.CAPTURE.COMPLETED", event, raw, "EVT-001")

        # Email sent only once despite two deliveries
        mock_email.assert_called_once()
        # Only one WebhookEvent row
        self.assertEqual(WebhookEvent.objects.filter(paypal_event_id="EVT-001").count(), 1)

    @patch("apps.donations.services.webhooks.send_receipt_email")
    def test_already_completed_donation_not_reprocessed(self, mock_email):
        self.donation.status = Donation.Status.COMPLETED
        self.donation.receipt_number = "AIM-2026-00001"
        self.donation.save()

        event = self._capture_event()
        handle_webhook(
            "PAYMENT.CAPTURE.COMPLETED",
            event,
            json.dumps(event).encode(),
            "EVT-002",
        )

        mock_email.assert_not_called()

    def test_capture_denied_marks_donation_failed(self):
        event = {
            "id": "EVT-003",
            "event_type": "PAYMENT.CAPTURE.DENIED",
            "resource": {
                "supplementary_data": {"related_ids": {"order_id": "ORDER-ABC"}}
            },
        }
        handle_webhook(
            "PAYMENT.CAPTURE.DENIED",
            event,
            json.dumps(event).encode(),
            "EVT-003",
        )

        self.donation.refresh_from_db()
        self.assertEqual(self.donation.status, Donation.Status.FAILED)

    def test_webhook_event_logged(self):
        event = self._capture_event()
        raw = json.dumps(event).encode()

        with patch("apps.donations.services.webhooks.send_receipt_email", return_value=True):
            handle_webhook("PAYMENT.CAPTURE.COMPLETED", event, raw, "EVT-LOG-1")

        self.assertTrue(WebhookEvent.objects.filter(paypal_event_id="EVT-LOG-1", processed=True).exists())


# ---------------------------------------------------------------------------
# View tests
# ---------------------------------------------------------------------------

class DonateViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.category = make_category()
        self.url = reverse("donations:donate")

    def test_get_renders_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Donate with PayPal")

    def test_post_invalid_shows_errors(self):
        response = self.client.post(self.url, data={})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter your full name")
        self.assertContains(response, "Please enter your email address")
        self.assertContains(response, "Please enter a donation amount")
        self.assertContains(response, "Please select a fund")

    @patch("apps.donations.views.create_order")
    def test_post_valid_creates_donation_and_redirects(self, mock_create):
        mock_create.return_value = {
            "order_id": "ORDER-NEW",
            "approve_url": "https://paypal.com/approve?token=ORDER-NEW",
        }
        response = self.client.post(self.url, data={
            "donor_name": "Jane Smith",
            "donor_email": "jane@example.com",
            "amount": "50.00",
            "category": self.category.pk,
        })
        self.assertRedirects(response, "https://paypal.com/approve?token=ORDER-NEW", fetch_redirect_response=False)
        donation = Donation.objects.get(paypal_order_id="ORDER-NEW")
        self.assertEqual(donation.donor_name, "Jane Smith")
        self.assertEqual(donation.amount, Decimal("50.00"))
        self.assertEqual(donation.status, Donation.Status.PENDING)

    @patch("apps.donations.views.create_order")
    def test_paypal_failure_shows_error_message(self, mock_create):
        mock_create.side_effect = Exception("PayPal down")
        response = self.client.post(self.url, data={
            "donor_name": "Jane Smith",
            "donor_email": "jane@example.com",
            "amount": "50.00",
            "category": self.category.pk,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "connect to PayPal")
        # Donation should be marked failed
        donation = Donation.objects.first()
        self.assertEqual(donation.status, Donation.Status.FAILED)


class PayPalReturnViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.category = make_category()
        self.donation = make_donation(self.category, paypal_order_id="ORDER-RET")

    @patch("apps.donations.views.capture_order")
    def test_return_with_valid_token_shows_success(self, mock_capture):
        mock_capture.return_value = {}
        url = reverse("donations:paypal_return") + "?token=ORDER-RET"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Thank you")

    def test_return_without_token_shows_cancel(self):
        url = reverse("donations:paypal_return")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No payment was made")

    def test_cancel_marks_donation_cancelled(self):
        url = reverse("donations:paypal_cancel") + "?token=ORDER-RET"
        self.client.get(url)
        self.donation.refresh_from_db()
        self.assertEqual(self.donation.status, Donation.Status.CANCELLED)


class AdminActionTests(TestCase):

    def setUp(self):
        self.site = AdminSite()
        self.model_admin = DonationAdmin(Donation, self.site)
        self.factory = RequestFactory()
        self.superuser = User.objects.create_superuser("admin", "admin@test.com", "password")
        self.category = make_category()

    def _make_completed(self, capture_id="CAP-TEST", **kwargs):
        return make_donation(
            self.category,
            status=Donation.Status.COMPLETED,
            paypal_capture_id=capture_id,
            receipt_number="AIM-2026-00001",
            completed_at=timezone.now(),
            **kwargs,
        )

    # --- CSV export ---

    def test_export_csv_returns_csv_response(self):
        d = self._make_completed()
        request = self.factory.get("/")
        request.user = self.superuser
        response = self.model_admin.export_csv(request, Donation.objects.filter(pk=d.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("donations_", response["Content-Disposition"])

    def test_export_csv_contains_donor_data(self):
        d = self._make_completed()
        request = self.factory.get("/")
        request.user = self.superuser
        response = self.model_admin.export_csv(request, Donation.objects.filter(pk=d.pk))
        content = response.content.decode()
        self.assertIn("Jane Smith", content)
        self.assertIn("jane@example.com", content)
        self.assertIn("100.00", content)
        self.assertIn("AIM-2026-00001", content)

    def test_export_csv_skips_no_rows_gracefully(self):
        request = self.factory.get("/")
        request.user = self.superuser
        response = self.model_admin.export_csv(request, Donation.objects.none())
        content = response.content.decode()
        # Header row still present
        self.assertIn("Receipt Number", content)

    # --- Refund ---

    @patch("apps.donations.admin.refund_capture")
    def test_refund_completed_donation(self, mock_refund):
        mock_refund.return_value = {"id": "REFUND-001", "status": "COMPLETED"}
        d = self._make_completed(capture_id="CAP-123")

        request = self.factory.post("/")
        request.user = self.superuser
        request._messages = []  # silence message framework in tests

        from django.contrib.messages.storage.fallback import FallbackStorage
        setattr(request, "session", {})
        setattr(request, "_messages", FallbackStorage(request))

        self.model_admin.process_refund(request, Donation.objects.filter(pk=d.pk))

        mock_refund.assert_called_once_with("CAP-123")
        d.refresh_from_db()
        self.assertEqual(d.status, Donation.Status.REFUNDED)

    @patch("apps.donations.admin.refund_capture")
    def test_refund_skips_non_completed(self, mock_refund):
        d = make_donation(self.category, status=Donation.Status.PENDING)

        request = self.factory.post("/")
        request.user = self.superuser
        from django.contrib.messages.storage.fallback import FallbackStorage
        setattr(request, "session", {})
        setattr(request, "_messages", FallbackStorage(request))

        self.model_admin.process_refund(request, Donation.objects.filter(pk=d.pk))

        mock_refund.assert_not_called()
        d.refresh_from_db()
        self.assertEqual(d.status, Donation.Status.PENDING)

    @patch("apps.donations.admin.refund_capture")
    def test_refund_handles_paypal_error_gracefully(self, mock_refund):
        mock_refund.side_effect = Exception("PayPal connection refused")
        d = self._make_completed(capture_id="CAP-FAIL", paypal_order_id="ORDER-FAIL")

        request = self.factory.post("/")
        request.user = self.superuser
        from django.contrib.messages.storage.fallback import FallbackStorage
        setattr(request, "session", {})
        setattr(request, "_messages", FallbackStorage(request))

        self.model_admin.process_refund(request, Donation.objects.filter(pk=d.pk))

        # Donation status must NOT change on failure
        d.refresh_from_db()
        self.assertEqual(d.status, Donation.Status.COMPLETED)


class WebhookViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse("donations:paypal_webhook")
        self.category = make_category()
        self.donation = make_donation(self.category, paypal_order_id="ORDER-WH")

    def _post_webhook(self, payload, verified=True):
        with patch("apps.donations.views.verify_webhook_signature", return_value=verified):
            return self.client.post(
                self.url,
                data=json.dumps(payload),
                content_type="application/json",
            )

    def test_invalid_signature_returns_400(self):
        response = self._post_webhook({}, verified=False)
        self.assertEqual(response.status_code, 400)

    @patch("apps.donations.services.webhooks.send_receipt_email", return_value=True)
    def test_valid_capture_completed_returns_200(self, mock_email):
        payload = {
            "id": "EVT-VIEW-1",
            "event_type": "PAYMENT.CAPTURE.COMPLETED",
            "resource": {
                "id": "CAP-VIEW-1",
                "purchase_units": [{"custom_id": str(self.donation.pk)}],
                "supplementary_data": {"related_ids": {"order_id": "ORDER-WH"}},
            },
        }
        response = self._post_webhook(payload)
        self.assertEqual(response.status_code, 200)

    def test_malformed_json_returns_400(self):
        with patch("apps.donations.views.verify_webhook_signature", return_value=True):
            response = self.client.post(
                self.url,
                data="not json{{{",
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 400)
