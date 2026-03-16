"""
Reimbursement system tests.

Coverage:
- Model properties and FSM transitions
- Service layer validation and state guards
- QuerySet filters
- View authorization and basic flows
- EncryptedCharField round-trip
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from people.models import People
from programs.models import Program
from enrollments.models import Enrollment

from .models import (
    ReimbursementRequest,
    ExpenseLineItem,
    RequestStatus,
    TaxStatus,
    PaymentMethod,
    ExpenseCategory,
    Currency,
)
from .services import (
    create_reimbursement_request,
    add_expense_line_item,
    submit_request,
    approve_request,
    mark_as_paid,
    cancel_request,
    request_changes,
    ValidationError,
    StateTransitionError,
)

User = get_user_model()


# =============================================================================
# HELPERS
# =============================================================================

def make_person(**kwargs):
    defaults = {"first_name": "Jane", "last_name": "Doe", "email_address": "jane@example.com"}
    defaults.update(kwargs)
    return People.objects.create(**defaults)


def make_user(username="testuser", is_staff=False, **kwargs):
    return User.objects.create_user(username=username, password="pass", is_staff=is_staff, **kwargs)


def make_program(**kwargs):
    defaults = {
        "title": "Test Workshop",
        "type": Program.ProgramType.WORKSHOP,
        "code": 9000,
        "start_date": date.today() + timedelta(days=30),
    }
    defaults.update(kwargs)
    return Program.objects.create(**defaults)


def make_draft(person, user, **kwargs):
    """Create a minimal DRAFT reimbursement request via the service."""
    defaults = dict(
        tax_status=TaxStatus.US_CITIZEN,
        payment_method=PaymentMethod.CHECK,
        payment_address="123 Main St, Springfield, IL",
    )
    defaults.update(kwargs)
    return create_reimbursement_request(person=person, submitted_by=user, **defaults)


def add_line_item(request, amount="50.00", **kwargs):
    defaults = dict(
        category=ExpenseCategory.AIRFARE,
        description="Flight to conference",
        date_incurred=date.today(),
        amount_requested=Decimal(amount),
    )
    defaults.update(kwargs)
    return add_expense_line_item(request, **defaults)


# =============================================================================
# MODEL: FSM TRANSITIONS
# =============================================================================

class FSMTransitionTests(TestCase):
    def setUp(self):
        self.person = make_person()
        self.user = make_user()
        self.staff = make_user("staff", is_staff=True)
        self.draft = make_draft(self.person, self.user)
        add_line_item(self.draft)

    def test_submit_transitions_to_submitted(self):
        req = submit_request(self.draft, "Jane Doe")
        self.assertEqual(req.status, RequestStatus.SUBMITTED)

    def test_submit_sets_submitted_at(self):
        req = submit_request(self.draft, "Jane Doe")
        self.assertIsNotNone(req.submitted_at)

    def test_submit_calculates_total_requested(self):
        req = submit_request(self.draft, "Jane Doe")
        self.assertEqual(req.total_requested, Decimal("50.00"))

    def test_cannot_submit_without_signature(self):
        self.draft.signature = ""
        self.assertFalse(self.draft.can_submit())

    def test_cannot_submit_without_line_items(self):
        empty = make_draft(self.person, make_user("user2"))
        empty.signature = "Jane Doe"
        self.assertFalse(empty.can_submit())

    def test_approve_transitions_from_submitted(self):
        req = submit_request(self.draft, "Jane Doe")
        approve_request(req, self.staff)
        self.assertEqual(req.status, RequestStatus.APPROVED)

    def test_approve_sets_approved_at_and_by(self):
        req = submit_request(self.draft, "Jane Doe")
        approve_request(req, self.staff)
        self.assertIsNotNone(req.approved_at)
        self.assertEqual(req.approved_by, self.staff)

    def test_mark_paid_transitions_from_approved(self):
        req = submit_request(self.draft, "Jane Doe")
        approve_request(req, self.staff)
        mark_as_paid(req, self.staff, payment_reference="CHK-001")
        self.assertEqual(req.status, RequestStatus.PAID)

    def test_mark_paid_defaults_total_paid_to_approved(self):
        req = submit_request(self.draft, "Jane Doe")
        approve_request(req, self.staff)
        mark_as_paid(req, self.staff)
        self.assertEqual(req.total_paid, req.total_approved)

    def test_request_changes_transitions_to_changes_needed(self):
        req = submit_request(self.draft, "Jane Doe")
        request_changes(req, self.staff, "Please attach receipts.")
        self.assertEqual(req.status, RequestStatus.CHANGES_NEEDED)

    def test_request_changes_stores_notes_and_reviewer(self):
        req = submit_request(self.draft, "Jane Doe")
        request_changes(req, self.staff, "Please attach receipts.")
        self.assertEqual(req.change_request_notes, "Please attach receipts.")
        self.assertEqual(req.reviewed_by, self.staff)

    def test_resubmit_from_changes_needed(self):
        req = submit_request(self.draft, "Jane Doe")
        request_changes(req, self.staff, "Fix this.")
        req.signature = "Jane Doe"
        req.submit()
        self.assertEqual(req.status, RequestStatus.SUBMITTED)

    def test_cancel_from_draft(self):
        cancel_request(self.draft, self.user, reason="No longer needed.")
        self.assertEqual(self.draft.status, RequestStatus.CANCELLED)

    def test_cancel_from_submitted(self):
        req = submit_request(self.draft, "Jane Doe")
        cancel_request(req, self.staff, reason="Duplicate.")
        self.assertEqual(req.status, RequestStatus.CANCELLED)

    def test_cannot_cancel_paid(self):
        req = submit_request(self.draft, "Jane Doe")
        approve_request(req, self.staff)
        mark_as_paid(req, self.staff)
        with self.assertRaises(StateTransitionError):
            cancel_request(req, self.staff)

    def test_cannot_approve_draft(self):
        with self.assertRaises(StateTransitionError):
            approve_request(self.draft, self.staff)

    def test_cannot_mark_paid_without_approving_first(self):
        req = submit_request(self.draft, "Jane Doe")
        with self.assertRaises(StateTransitionError):
            mark_as_paid(req, self.staff)


# =============================================================================
# MODEL: PROPERTIES
# =============================================================================

class ModelPropertyTests(TestCase):
    def setUp(self):
        self.person = make_person()
        self.user = make_user()
        self.staff = make_user("staff", is_staff=True)
        self.draft = make_draft(self.person, self.user)

    def test_is_editable_draft(self):
        self.assertTrue(self.draft.is_editable)

    def test_is_editable_changes_needed(self):
        add_line_item(self.draft)
        req = submit_request(self.draft, "Jane Doe")
        request_changes(req, self.staff, "Fix.")
        self.assertTrue(req.is_editable)

    def test_is_not_editable_submitted(self):
        add_line_item(self.draft)
        req = submit_request(self.draft, "Jane Doe")
        self.assertFalse(req.is_editable)

    def test_is_not_editable_paid(self):
        add_line_item(self.draft)
        req = submit_request(self.draft, "Jane Doe")
        approve_request(req, self.staff)
        mark_as_paid(req, self.staff)
        self.assertFalse(req.is_editable)

    def test_requires_visa_docs_nonresident(self):
        req = make_draft(
            self.person, make_user("u2"),
            tax_status=TaxStatus.VISA_NONRESIDENT,
            citizenship_country="Germany",
        )
        self.assertTrue(req.requires_visa_docs)

    def test_requires_visa_docs_resident(self):
        req = make_draft(
            self.person, make_user("u3"),
            tax_status=TaxStatus.VISA_RESIDENT,
            citizenship_country="Germany",
        )
        self.assertTrue(req.requires_visa_docs)

    def test_does_not_require_visa_docs_us_citizen(self):
        self.assertFalse(self.draft.requires_visa_docs)

    def test_does_not_require_visa_docs_green_card(self):
        req = make_draft(self.person, make_user("u4"), tax_status=TaxStatus.GREEN_CARD)
        self.assertFalse(req.requires_visa_docs)

    def test_calculate_total_requested_sums_line_items(self):
        add_line_item(self.draft, amount="100.00")
        add_line_item(self.draft, amount="50.00")
        self.assertEqual(self.draft.calculate_total_requested(), Decimal("150.00"))

    def test_calculate_total_requested_empty(self):
        self.assertEqual(self.draft.calculate_total_requested(), Decimal("0.00"))

    def test_calculate_total_approved(self):
        item = add_line_item(self.draft, amount="100.00")
        item.amount_approved = Decimal("80.00")
        item.save()
        self.assertEqual(self.draft.calculate_total_approved(), Decimal("80.00"))

    def test_program_property_with_enrollment(self):
        program = make_program()
        enrollment = Enrollment.objects.create(workshop=program, person=self.person)
        req = make_draft(self.person, make_user("u5"), enrollment=enrollment)
        self.assertEqual(req.program, program)

    def test_program_property_without_enrollment(self):
        self.assertIsNone(self.draft.program)


# =============================================================================
# MODEL: FREEZE SNAPSHOTS
# =============================================================================

class FreezeSnapshotTests(TestCase):
    def setUp(self):
        self.person = make_person()
        self.user = make_user()

    def test_snapshot_captured_on_submit(self):
        req = make_draft(self.person, self.user)
        add_line_item(req)
        submit_request(req, "Jane Doe")
        self.assertIsNotNone(req.tax_info_snapshot)
        self.assertIsNotNone(req.payment_info_snapshot)

    def test_tax_snapshot_records_status(self):
        req = make_draft(self.person, self.user)
        add_line_item(req)
        submit_request(req, "Jane Doe")
        self.assertEqual(req.tax_info_snapshot["tax_status"], TaxStatus.US_CITIZEN)

    def test_payment_snapshot_records_method(self):
        req = make_draft(self.person, self.user)
        add_line_item(req)
        submit_request(req, "Jane Doe")
        self.assertEqual(req.payment_info_snapshot["payment_method"], PaymentMethod.CHECK)

    def test_payment_snapshot_stores_last4_not_full_account(self):
        req = make_draft(
            self.person, self.user,
            payment_method=PaymentMethod.ACH,
            payment_address="",
            bank_name="First Bank",
            bank_routing_number="021000021",
            bank_account_number="1234567890",
            bank_account_type="checking",
        )
        add_line_item(req)
        submit_request(req, "Jane Doe")
        snapshot = req.payment_info_snapshot
        self.assertEqual(snapshot["bank_account_last4"], "7890")
        self.assertNotIn("bank_account_number", snapshot)

    def test_passport_snapshot_stores_last4_only(self):
        req = make_draft(
            self.person, self.user,
            tax_status=TaxStatus.VISA_NONRESIDENT,
            citizenship_country="Germany",
            visa_type="J-1",
            passport_number="AB123456",
        )
        # Call _freeze_snapshots directly to test without needing a passport file
        req.signature = "Jane Doe"
        req._freeze_snapshots()
        self.assertEqual(req.tax_info_snapshot["passport_last4"], "3456")
        self.assertNotIn("passport_number", req.tax_info_snapshot)


# =============================================================================
# SERVICE: VALIDATION
# =============================================================================

class ServiceValidationTests(TestCase):
    def setUp(self):
        self.person = make_person()
        self.staff = make_user("staff", is_staff=True)

    def _user(self, name="u"):
        return make_user(name)

    def test_create_check_requires_address(self):
        with self.assertRaises(ValidationError):
            create_reimbursement_request(
                person=self.person,
                submitted_by=self._user("u1"),
                tax_status=TaxStatus.US_CITIZEN,
                payment_method=PaymentMethod.CHECK,
                payment_address="",
            )

    def test_create_ach_requires_all_bank_fields(self):
        with self.assertRaises(ValidationError):
            create_reimbursement_request(
                person=self.person,
                submitted_by=self._user("u2"),
                tax_status=TaxStatus.US_CITIZEN,
                payment_method=PaymentMethod.ACH,
                bank_name="First Bank",
                # routing and account missing
            )

    def test_create_visa_requires_citizenship_country(self):
        with self.assertRaises(ValidationError):
            create_reimbursement_request(
                person=self.person,
                submitted_by=self._user("u3"),
                tax_status=TaxStatus.VISA_NONRESIDENT,
                payment_method=PaymentMethod.CHECK,
                payment_address="123 Main St",
                citizenship_country="",
            )

    def test_submit_requires_signature(self):
        user = self._user("u4")
        req = make_draft(self.person, user)
        add_line_item(req)
        with self.assertRaises(ValidationError):
            submit_request(req, signature="")

    def test_submit_requires_at_least_one_line_item(self):
        user = self._user("u5")
        req = make_draft(self.person, user)
        with self.assertRaises(ValidationError):
            submit_request(req, "Jane Doe")

    def test_request_changes_requires_notes(self):
        user = self._user("u6")
        req = make_draft(self.person, user)
        add_line_item(req)
        req = submit_request(req, "Jane Doe")
        with self.assertRaises(ValidationError):
            request_changes(req, self.staff, notes="")

    def test_request_changes_on_draft_raises(self):
        user = self._user("u7")
        req = make_draft(self.person, user)
        with self.assertRaises(StateTransitionError):
            request_changes(req, self.staff, "Some notes")

    def test_add_expense_to_submitted_raises(self):
        user = self._user("u8")
        req = make_draft(self.person, user)
        add_line_item(req)
        req = submit_request(req, "Jane Doe")
        with self.assertRaises(StateTransitionError):
            add_line_item(req)

    def test_add_expense_zero_amount_raises(self):
        user = self._user("u9")
        req = make_draft(self.person, user)
        with self.assertRaises(ValidationError):
            add_expense_line_item(
                req,
                category=ExpenseCategory.AIRFARE,
                description="Test",
                date_incurred=date.today(),
                amount_requested=Decimal("0.00"),
            )

    def test_approve_defaults_amounts_to_requested(self):
        user = self._user("u10")
        req = make_draft(self.person, user)
        item = add_line_item(req, amount="75.00")
        req = submit_request(req, "Jane Doe")
        approve_request(req, self.staff)
        item.refresh_from_db()
        self.assertEqual(item.amount_approved, Decimal("75.00"))

    def test_approve_with_custom_amounts(self):
        user = self._user("u11")
        req = make_draft(self.person, user)
        item = add_line_item(req, amount="100.00")
        req = submit_request(req, "Jane Doe")
        approve_request(req, self.staff, approved_amounts={item.id: Decimal("60.00")})
        item.refresh_from_db()
        self.assertEqual(item.amount_approved, Decimal("60.00"))

    def test_mark_paid_custom_total_overrides_approved(self):
        user = self._user("u12")
        req = make_draft(self.person, user)
        add_line_item(req, amount="100.00")
        req = submit_request(req, "Jane Doe")
        approve_request(req, self.staff)
        mark_as_paid(req, self.staff, total_paid=Decimal("95.00"))
        self.assertEqual(req.total_paid, Decimal("95.00"))

    def test_cancel_already_cancelled_raises(self):
        user = self._user("u13")
        req = make_draft(self.person, user)
        cancel_request(req, user)
        with self.assertRaises(StateTransitionError):
            cancel_request(req, user)


# =============================================================================
# QUERYSET FILTERS
# =============================================================================

class QuerySetTests(TestCase):
    def setUp(self):
        self.person = make_person()
        self.user = make_user()
        self.staff = make_user("staff", is_staff=True)

        self.draft = make_draft(self.person, self.user)

        self.submitted = make_draft(self.person, make_user("u2"))
        add_line_item(self.submitted)
        submit_request(self.submitted, "Jane Doe")

        self.approved = make_draft(self.person, make_user("u3"))
        add_line_item(self.approved)
        submit_request(self.approved, "Jane Doe")
        approve_request(self.approved, self.staff)

        self.paid = make_draft(self.person, make_user("u4"))
        add_line_item(self.paid)
        submit_request(self.paid, "Jane Doe")
        approve_request(self.paid, self.staff)
        mark_as_paid(self.paid, self.staff)

        self.cancelled = make_draft(self.person, make_user("u5"))
        cancel_request(self.cancelled, self.user)

    def test_pending_review_returns_submitted_only(self):
        qs = ReimbursementRequest.objects.pending_review()
        self.assertIn(self.submitted, qs)
        self.assertNotIn(self.draft, qs)
        self.assertNotIn(self.approved, qs)

    def test_pending_payment_returns_approved_only(self):
        qs = ReimbursementRequest.objects.pending_payment()
        self.assertIn(self.approved, qs)
        self.assertNotIn(self.submitted, qs)
        self.assertNotIn(self.paid, qs)

    def test_needs_attention_returns_changes_needed(self):
        req = make_draft(self.person, make_user("u6"))
        add_line_item(req)
        submit_request(req, "Jane Doe")
        request_changes(req, self.staff, "Fix this.")
        qs = ReimbursementRequest.objects.needs_attention()
        self.assertIn(req, qs)
        self.assertNotIn(self.submitted, qs)

    def test_completed_includes_paid_and_cancelled(self):
        qs = ReimbursementRequest.objects.completed()
        self.assertIn(self.paid, qs)
        self.assertIn(self.cancelled, qs)
        self.assertNotIn(self.submitted, qs)
        self.assertNotIn(self.draft, qs)

    def test_for_user_filters_by_submitted_by(self):
        other_person = make_person(email_address="other@example.com")
        other_user = make_user("other_u")
        other_req = make_draft(other_person, other_user)
        qs = ReimbursementRequest.objects.for_user(self.user)
        self.assertIn(self.draft, qs)
        self.assertNotIn(other_req, qs)

    def test_for_person_filters_by_payee(self):
        other_person = make_person(email_address="other2@example.com")
        other_req = make_draft(other_person, make_user("other_u2"))
        qs = ReimbursementRequest.objects.for_person(self.person)
        self.assertIn(self.draft, qs)
        self.assertNotIn(other_req, qs)


# =============================================================================
# ENCRYPTION FIELD
# =============================================================================

class EncryptedFieldTests(TestCase):
    def setUp(self):
        self.person = make_person()
        self.user = make_user()

    def _make_ach_request(self, routing="021000021", account="987654321"):
        return make_draft(
            self.person, self.user,
            payment_method=PaymentMethod.ACH,
            payment_address="",
            bank_name="First Bank",
            bank_routing_number=routing,
            bank_account_number=account,
            bank_account_type="checking",
        )

    def test_routing_number_not_stored_in_plaintext(self):
        req = self._make_ach_request()
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT bank_routing_number FROM reimbursements_reimbursementrequest WHERE id = %s",
                [req.pk]
            )
            raw = cursor.fetchone()[0]
        self.assertNotEqual(raw, "021000021")
        self.assertGreater(len(raw), 20)

    def test_routing_number_decrypts_on_access(self):
        req = self._make_ach_request()
        fetched = ReimbursementRequest.objects.get(pk=req.pk)
        self.assertEqual(fetched.bank_routing_number, "021000021")

    def test_account_number_decrypts_on_access(self):
        req = self._make_ach_request()
        fetched = ReimbursementRequest.objects.get(pk=req.pk)
        self.assertEqual(fetched.bank_account_number, "987654321")

    def test_empty_string_not_encrypted(self):
        req = make_draft(self.person, self.user)
        fetched = ReimbursementRequest.objects.get(pk=req.pk)
        self.assertEqual(fetched.bank_routing_number, "")

    def test_encryption_is_unique_per_save(self):
        """Two saves of the same value should produce different ciphertext."""
        req1 = self._make_ach_request(routing="021000021")
        req2 = self._make_ach_request(routing="021000021")
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT bank_routing_number FROM reimbursements_reimbursementrequest WHERE id IN (%s, %s)",
                [req1.pk, req2.pk]
            )
            rows = cursor.fetchall()
        # Fernet uses random IV so same plaintext → different ciphertext
        self.assertNotEqual(rows[0][0], rows[1][0])


# =============================================================================
# VIEWS: AUTHORIZATION
# =============================================================================

class ViewAuthorizationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.person = make_person()
        self.user = make_user()
        self.other_user = make_user("other")
        self.staff = make_user("staff", is_staff=True)
        self.req = make_draft(self.person, self.user)

    def test_my_reimbursements_requires_login(self):
        response = self.client.get(reverse("reimbursements:my_reimbursements"))
        self.assertNotEqual(response.status_code, 200)

    def test_detail_requires_login(self):
        response = self.client.get(reverse("reimbursements:detail", args=[self.req.pk]))
        self.assertNotEqual(response.status_code, 200)

    def test_edit_requires_login(self):
        response = self.client.get(reverse("reimbursements:edit", args=[self.req.pk]))
        self.assertNotEqual(response.status_code, 200)

    def test_other_user_cannot_view_detail(self):
        self.client.login(username="other", password="pass")
        response = self.client.get(reverse("reimbursements:detail", args=[self.req.pk]))
        self.assertEqual(response.status_code, 404)

    def test_other_user_cannot_edit(self):
        self.client.login(username="other", password="pass")
        response = self.client.get(reverse("reimbursements:edit", args=[self.req.pk]))
        self.assertEqual(response.status_code, 404)

    def test_staff_can_view_any_detail(self):
        self.client.login(username="staff", password="pass")
        response = self.client.get(reverse("reimbursements:detail", args=[self.req.pk]))
        self.assertEqual(response.status_code, 200)

    def test_owner_can_view_detail(self):
        self.client.login(username="testuser", password="pass")
        response = self.client.get(reverse("reimbursements:detail", args=[self.req.pk]))
        self.assertEqual(response.status_code, 200)

    def test_owner_can_access_edit(self):
        self.client.login(username="testuser", password="pass")
        response = self.client.get(reverse("reimbursements:edit", args=[self.req.pk]))
        self.assertEqual(response.status_code, 200)


class ViewEditFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.person = make_person()
        self.user = make_user()
        self.staff = make_user("staff", is_staff=True)
        self.client.login(username="testuser", password="pass")
        self.req = make_draft(self.person, self.user)

    def test_editing_submitted_request_redirects_to_detail(self):
        add_line_item(self.req)
        submit_request(self.req, "Jane Doe")
        response = self.client.get(reverse("reimbursements:edit", args=[self.req.pk]))
        self.assertRedirects(response, reverse("reimbursements:detail", args=[self.req.pk]))

    def _status(self):
        return ReimbursementRequest.objects.get(pk=self.req.pk).status

    def test_cancel_draft_via_post(self):
        self.client.post(
            reverse("reimbursements:cancel", args=[self.req.pk]),
            {"reason": "Changed my mind."}
        )
        self.assertEqual(self._status(), RequestStatus.CANCELLED)

    def test_cannot_cancel_paid_request(self):
        add_line_item(self.req)
        submit_request(self.req, "Jane Doe")
        approve_request(self.req, self.staff)
        mark_as_paid(self.req, self.staff)
        self.client.post(
            reverse("reimbursements:cancel", args=[self.req.pk]),
            {"reason": "Too late."}
        )
        self.assertEqual(self._status(), RequestStatus.PAID)

    def test_submit_without_expenses_stays_draft(self):
        self.client.post(
            reverse("reimbursements:submit", args=[self.req.pk]),
            {
                "signature": "Jane Doe",
                "certify_accurate": True,
                "certify_honoraria": True,
                "certify_no_duplicate": True,
            }
        )
        self.assertEqual(self._status(), RequestStatus.DRAFT)

    def test_my_reimbursements_shows_only_own_requests(self):
        other_user = make_user("other2")
        other_person = make_person(email_address="other2@example.com")
        other_req = make_draft(other_person, other_user)
        response = self.client.get(reverse("reimbursements:my_reimbursements"))
        self.assertEqual(response.status_code, 200)
        pks = [r.pk for r in response.context["requests"]]
        self.assertIn(self.req.pk, pks)
        self.assertNotIn(other_req.pk, pks)
