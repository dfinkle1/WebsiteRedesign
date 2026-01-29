"""
Reimbursement System Models

This module defines the data model for AIM's reimbursement system.
Key entities:
- ReimbursementRequest: The main request with workflow status
- ExpenseLineItem: Individual expenses within a request
- Receipt: File attachments for expenses
"""

from decimal import Decimal
from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils import timezone
from django_fsm import FSMField, transition

from people.models import People
from enrollments.models import Enrollment


# =============================================================================
# ABSTRACT BASE MODELS
# =============================================================================


class TimestampedModel(models.Model):
    """Abstract base class providing created/updated timestamps."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# =============================================================================
# CHOICES
# =============================================================================


class RequestStatus(models.TextChoices):
    """Reimbursement request workflow states."""

    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted"
    CHANGES_NEEDED = "changes_needed", "Changes Needed"
    APPROVED = "approved", "Approved"
    PAID = "paid", "Paid"
    CANCELLED = "cancelled", "Cancelled"


class TaxStatus(models.TextChoices):
    """US tax status for payment processing."""

    US_CITIZEN = "us_citizen", "US Citizen"
    GREEN_CARD = "green_card", "Green Card Holder"
    VISA_RESIDENT = "visa_resident", "Visa Holder - Resident for Tax Purposes"
    VISA_NONRESIDENT = "visa_nonresident", "Visa Holder - Non-Resident for Tax Purposes"


class PaymentMethod(models.TextChoices):
    """How the reimbursement will be paid."""

    CHECK = "check", "Check (mailed)"
    ACH = "ach", "Direct Deposit (ACH)"


class ExpenseCategory(models.TextChoices):
    """Categories for expense line items."""

    AIRFARE = "airfare", "Airfare"
    GROUND_TRANSPORT = "ground", "Ground Transportation"
    LODGING = "lodging", "Lodging"
    MEALS = "meals", "Meals / Per Diem"
    BAGGAGE = "baggage", "Baggage Fees"
    OTHER = "other", "Other"


# =============================================================================
# MANAGERS / QUERYSETS
# =============================================================================


class ReimbursementRequestQuerySet(models.QuerySet):
    """Custom queryset with common filters for reimbursement requests."""

    def pending_review(self):
        """Requests awaiting staff review."""
        return self.filter(status=RequestStatus.SUBMITTED)

    def pending_payment(self):
        """Approved requests awaiting payment."""
        return self.filter(status=RequestStatus.APPROVED)

    def needs_attention(self):
        """Requests needing action from submitter."""
        return self.filter(status=RequestStatus.CHANGES_NEEDED)

    def completed(self):
        """Paid or cancelled requests."""
        return self.filter(status__in=[RequestStatus.PAID, RequestStatus.CANCELLED])

    def for_program(self, program):
        """Filter by program (via enrollment)."""
        return self.filter(enrollment__workshop=program)

    def for_user(self, user):
        """Requests submitted by a specific user."""
        return self.filter(submitted_by=user)

    def for_person(self, person):
        """Requests for a specific person (as payee)."""
        return self.filter(person=person)

    def with_totals(self):
        """Annotate with calculated totals from line items."""
        return self.annotate(
            calculated_requested=Sum("line_items__amount_requested"),
            calculated_approved=Sum("line_items__amount_approved"),
        )


# =============================================================================
# MAIN MODELS
# =============================================================================


def visa_document_upload_path(instance, filename):
    """Upload path for visa-related documents."""
    return f"reimbursements/{instance.id}/visa_docs/{filename}"


class ReimbursementRequest(TimestampedModel):
    """
    A request for reimbursement of expenses related to a program.

    Lifecycle:
        DRAFT → SUBMITTED → APPROVED → PAID
                    ↓
              CHANGES_NEEDED → SUBMITTED (resubmit)

        Any state except PAID can → CANCELLED
    """

    # -------------------------------------------------------------------------
    # RELATIONSHIPS
    # -------------------------------------------------------------------------

    # Who is being reimbursed (the payee)
    person = models.ForeignKey(
        People,
        on_delete=models.PROTECT,
        related_name="reimbursement_requests",
        help_text="The person being reimbursed.",
    )

    # Optional: link to program attendance (null for staff/vendor reimbursements)
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reimbursement_requests",
        help_text="The program enrollment this reimbursement is for. Leave blank for staff/vendor.",
    )

    # Who submitted this request (may be different from person if staff submits)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="submitted_reimbursements",
        help_text="The user who submitted this request.",
    )

    # -------------------------------------------------------------------------
    # WORKFLOW STATUS (FSM)
    # -------------------------------------------------------------------------

    status = FSMField(
        default=RequestStatus.DRAFT,
        choices=RequestStatus.choices,
        protected=True,  # Prevent direct assignment, must use transitions
        db_index=True,
    )

    # -------------------------------------------------------------------------
    # TAX INFORMATION
    # -------------------------------------------------------------------------

    tax_status = models.CharField(
        max_length=20,
        choices=TaxStatus.choices,
        help_text="Tax status determines required documentation.",
    )

    # Visa holder fields (required only if tax_status is visa_*)
    citizenship_country = models.CharField(
        max_length=100,
        blank=True,
        help_text="Country of citizenship (visa holders only).",
    )
    visa_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Visa type, e.g., J-1, F-1, H-1B.",
    )
    passport_number = models.CharField(
        max_length=50,
        blank=True,
    )
    passport_copy = models.FileField(
        upload_to=visa_document_upload_path,
        blank=True,
        null=True,
        help_text="Copy of passport photo page.",
    )
    us_entry_date = models.DateField(
        null=True,
        blank=True,
        help_text="Most recent US entry date.",
    )
    i94_document = models.FileField(
        upload_to=visa_document_upload_path,
        blank=True,
        null=True,
        help_text="Most recent I-94 document.",
    )

    # Snapshot of tax info at submission (for audit)
    tax_info_snapshot = models.JSONField(
        null=True,
        blank=True,
        help_text="Frozen copy of tax info at submission time.",
    )

    # -------------------------------------------------------------------------
    # PAYMENT INFORMATION
    # -------------------------------------------------------------------------

    payment_method = models.CharField(
        max_length=10,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CHECK,
    )

    # Check payment fields
    payment_address = models.TextField(
        blank=True,
        help_text="Mailing address for check payments.",
    )

    # ACH payment fields
    bank_name = models.CharField(max_length=100, blank=True)
    bank_routing_number = models.CharField(max_length=9, blank=True)
    bank_account_number = models.CharField(max_length=17, blank=True)
    bank_account_type = models.CharField(
        max_length=10,
        choices=[("checking", "Checking"), ("savings", "Savings")],
        blank=True,
    )

    # Snapshot of payment info at submission (for audit)
    payment_info_snapshot = models.JSONField(
        null=True,
        blank=True,
        help_text="Frozen copy of payment info at submission time.",
    )

    # -------------------------------------------------------------------------
    # FINANCIAL TOTALS
    # -------------------------------------------------------------------------

    total_requested = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Sum of all requested amounts (calculated on submit).",
    )
    total_approved = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Sum of approved amounts (set on approval).",
    )
    total_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Actual amount paid (may differ from approved).",
    )

    # -------------------------------------------------------------------------
    # AUDIT TRAIL
    # -------------------------------------------------------------------------

    submitted_at = models.DateTimeField(null=True, blank=True)

    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reviewed_reimbursements",
    )

    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_reimbursements",
    )

    paid_at = models.DateTimeField(null=True, blank=True)
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="paid_reimbursements",
    )
    payment_reference = models.CharField(
        max_length=100,
        blank=True,
        help_text="Check number, wire reference, or transaction ID.",
    )

    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="cancelled_reimbursements",
    )
    cancellation_reason = models.TextField(blank=True)

    # -------------------------------------------------------------------------
    # NOTES
    # -------------------------------------------------------------------------

    submitter_notes = models.TextField(
        blank=True,
        help_text="Notes from the submitter.",
    )
    reviewer_notes = models.TextField(
        blank=True,
        help_text="Internal notes from reviewer (not shown to submitter).",
    )
    change_request_notes = models.TextField(
        blank=True,
        help_text="Explanation of what changes are needed.",
    )

    # -------------------------------------------------------------------------
    # SIGNATURE
    # -------------------------------------------------------------------------

    signature = models.CharField(
        max_length=255,
        blank=True,
        help_text="Digital signature (typed name).",
    )
    signed_at = models.DateTimeField(null=True, blank=True)

    # -------------------------------------------------------------------------
    # MANAGERS
    # -------------------------------------------------------------------------

    objects = ReimbursementRequestQuerySet.as_manager()

    # -------------------------------------------------------------------------
    # META
    # -------------------------------------------------------------------------

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Reimbursement Request"
        verbose_name_plural = "Reimbursement Requests"
        permissions = [
            ("can_review", "Can review reimbursement requests"),
            ("can_approve", "Can approve reimbursement requests"),
            ("can_mark_paid", "Can mark reimbursements as paid"),
            ("can_export", "Can export reimbursement data"),
        ]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["person", "-created_at"]),
            models.Index(fields=["submitted_by", "-created_at"]),
        ]

    def __str__(self):
        program_str = ""
        if self.enrollment and self.enrollment.workshop:
            program_str = f" - {self.enrollment.workshop.title}"
        return f"Reimbursement #{self.pk}: {self.person}{program_str}"

    # -------------------------------------------------------------------------
    # CALCULATED PROPERTIES
    # -------------------------------------------------------------------------

    def calculate_total_requested(self) -> Decimal:
        """Calculate sum of all line item requested amounts."""
        total = self.line_items.aggregate(total=Sum("amount_requested"))["total"]
        return total or Decimal("0.00")

    def calculate_total_approved(self) -> Decimal:
        """Calculate sum of all line item approved amounts."""
        total = self.line_items.aggregate(total=Sum("amount_approved"))["total"]
        return total or Decimal("0.00")

    @property
    def is_editable(self) -> bool:
        """Can the submitter edit this request?"""
        return self.status in [RequestStatus.DRAFT, RequestStatus.CHANGES_NEEDED]

    @property
    def requires_visa_docs(self) -> bool:
        """Does this request require visa documentation?"""
        return self.tax_status in [TaxStatus.VISA_RESIDENT, TaxStatus.VISA_NONRESIDENT]

    @property
    def program(self):
        """Convenience property to get the program."""
        if self.enrollment:
            return self.enrollment.workshop
        return None

    # -------------------------------------------------------------------------
    # FSM TRANSITIONS
    # -------------------------------------------------------------------------

    def can_submit(self):
        """Check if request can be submitted."""
        # Must have at least one line item
        if not self.line_items.exists():
            return False
        # Must have signature
        if not self.signature:
            return False
        # If visa holder, must have required docs
        if self.requires_visa_docs and not self.passport_copy:
            return False
        return True

    @transition(
        field=status,
        source=[RequestStatus.DRAFT, RequestStatus.CHANGES_NEEDED],
        target=RequestStatus.SUBMITTED,
        conditions=[can_submit],
    )
    def submit(self):
        """Submit the request for review."""
        self.submitted_at = timezone.now()
        self.total_requested = self.calculate_total_requested()
        # Freeze tax and payment info
        self._freeze_snapshots()

    @transition(
        field=status,
        source=RequestStatus.SUBMITTED,
        target=RequestStatus.CHANGES_NEEDED,
    )
    def request_changes(self, notes: str = ""):
        """Send back to submitter for changes."""
        self.reviewed_at = timezone.now()
        self.change_request_notes = notes

    @transition(
        field=status,
        source=RequestStatus.SUBMITTED,
        target=RequestStatus.APPROVED,
    )
    def approve(self):
        """Approve the request for payment."""
        self.approved_at = timezone.now()
        self.total_approved = self.calculate_total_approved()

    @transition(
        field=status,
        source=RequestStatus.APPROVED,
        target=RequestStatus.PAID,
    )
    def mark_paid(self, payment_reference: str = ""):
        """Mark the request as paid."""
        self.paid_at = timezone.now()
        self.payment_reference = payment_reference
        self.total_paid = self.total_approved

    @transition(
        field=status,
        source=[
            RequestStatus.DRAFT,
            RequestStatus.SUBMITTED,
            RequestStatus.CHANGES_NEEDED,
            RequestStatus.APPROVED,
        ],
        target=RequestStatus.CANCELLED,
    )
    def cancel(self, reason: str = ""):
        """Cancel the request."""
        self.cancelled_at = timezone.now()
        self.cancellation_reason = reason

    # -------------------------------------------------------------------------
    # PRIVATE METHODS
    # -------------------------------------------------------------------------

    def _freeze_snapshots(self):
        """Freeze tax and payment info at submission time."""
        self.tax_info_snapshot = {
            "tax_status": self.tax_status,
            "citizenship_country": self.citizenship_country,
            "visa_type": self.visa_type,
            "passport_number": self.passport_number,
            "us_entry_date": str(self.us_entry_date) if self.us_entry_date else None,
        }
        self.payment_info_snapshot = {
            "payment_method": self.payment_method,
            "payment_address": self.payment_address,
            "bank_name": self.bank_name,
            # Note: Don't store full account numbers in snapshot for security
            "bank_account_last4": self.bank_account_number[-4:] if self.bank_account_number else "",
        }


def receipt_upload_path(instance, filename):
    """Upload path for receipt files."""
    request_id = instance.line_item.request_id
    return f"reimbursements/{request_id}/receipts/{filename}"


class ExpenseLineItem(TimestampedModel):
    """
    An individual expense within a reimbursement request.

    Each line item can have multiple receipts attached.
    """

    request = models.ForeignKey(
        ReimbursementRequest,
        on_delete=models.CASCADE,
        related_name="line_items",
    )

    category = models.CharField(
        max_length=20,
        choices=ExpenseCategory.choices,
        default=ExpenseCategory.OTHER,
    )
    description = models.CharField(
        max_length=255,
        help_text="Brief description of the expense.",
    )
    date_incurred = models.DateField(
        help_text="Date the expense was incurred.",
    )

    amount_requested = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Amount being requested for reimbursement (USD).",
    )
    amount_approved = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Amount approved by reviewer (may be less than requested).",
    )

    reviewer_notes = models.TextField(
        blank=True,
        help_text="Notes from reviewer about this line item.",
    )

    class Meta:
        ordering = ["date_incurred", "id"]
        verbose_name = "Expense Line Item"
        verbose_name_plural = "Expense Line Items"

    def __str__(self):
        return f"{self.get_category_display()}: ${self.amount_requested}"


class Receipt(TimestampedModel):
    """
    A receipt or supporting document for an expense line item.

    Multiple receipts can be attached to a single line item.
    """

    line_item = models.ForeignKey(
        ExpenseLineItem,
        on_delete=models.CASCADE,
        related_name="receipts",
    )

    file = models.FileField(
        upload_to=receipt_upload_path,
        help_text="PDF, JPG, or PNG file.",
    )
    original_filename = models.CharField(
        max_length=255,
        help_text="Original filename when uploaded.",
    )
    file_size = models.PositiveIntegerField(
        help_text="File size in bytes.",
    )

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Receipt"
        verbose_name_plural = "Receipts"

    def __str__(self):
        return self.original_filename

    def save(self, *args, **kwargs):
        if self.file and not self.original_filename:
            self.original_filename = self.file.name
        if self.file and not self.file_size:
            self.file_size = self.file.size
        super().save(*args, **kwargs)


