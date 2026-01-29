"""
Reimbursement Business Logic Services

This module contains the business logic for reimbursement operations.
Use these functions instead of manipulating models directly to ensure
proper validation, audit trails, and state transitions.
"""

from decimal import Decimal
from typing import Optional

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .models import (
    ReimbursementRequest,
    ExpenseLineItem,
    Receipt,
    RequestStatus,
    TaxStatus,
)
from people.models import People
from enrollments.models import Enrollment

User = get_user_model()


class ReimbursementError(Exception):
    """Base exception for reimbursement operations."""

    pass


class ValidationError(ReimbursementError):
    """Raised when validation fails."""

    pass


class StateTransitionError(ReimbursementError):
    """Raised when an invalid state transition is attempted."""

    pass


# =============================================================================
# CREATE OPERATIONS
# =============================================================================


@transaction.atomic
def create_reimbursement_request(
    person: People,
    submitted_by: User,
    tax_status: str,
    payment_method: str,
    payment_address: str = "",
    enrollment: Optional[Enrollment] = None,
    # ACH fields
    bank_name: str = "",
    bank_routing_number: str = "",
    bank_account_number: str = "",
    bank_account_type: str = "",
    # Visa fields (required if tax_status is visa_*)
    citizenship_country: str = "",
    visa_type: str = "",
    passport_number: str = "",
    us_entry_date=None,
    # Notes
    submitter_notes: str = "",
) -> ReimbursementRequest:
    """
    Create a new reimbursement request in DRAFT status.

    Args:
        person: The person being reimbursed
        submitted_by: The user creating the request
        tax_status: One of TaxStatus choices
        payment_method: 'check' or 'ach'
        payment_address: Required if payment_method is 'check'
        enrollment: Optional enrollment (for participant reimbursements)
        bank_*: Required if payment_method is 'ach'
        citizenship_country, visa_type, etc.: Required if tax_status is visa_*
        submitter_notes: Optional notes from submitter

    Returns:
        The created ReimbursementRequest in DRAFT status

    Raises:
        ValidationError: If required fields are missing
    """
    # Validate payment method requirements
    if payment_method == "check" and not payment_address:
        raise ValidationError("Payment address is required for check payments.")

    if payment_method == "ach":
        if not all([bank_name, bank_routing_number, bank_account_number, bank_account_type]):
            raise ValidationError("All bank details are required for ACH payments.")

    # Validate visa requirements
    if tax_status in [TaxStatus.VISA_RESIDENT, TaxStatus.VISA_NONRESIDENT]:
        if not citizenship_country:
            raise ValidationError("Citizenship country is required for visa holders.")

    request = ReimbursementRequest.objects.create(
        person=person,
        submitted_by=submitted_by,
        enrollment=enrollment,
        tax_status=tax_status,
        payment_method=payment_method,
        payment_address=payment_address,
        bank_name=bank_name,
        bank_routing_number=bank_routing_number,
        bank_account_number=bank_account_number,
        bank_account_type=bank_account_type,
        citizenship_country=citizenship_country,
        visa_type=visa_type,
        passport_number=passport_number,
        us_entry_date=us_entry_date,
        submitter_notes=submitter_notes,
    )

    return request


@transaction.atomic
def add_expense_line_item(
    request: ReimbursementRequest,
    category: str,
    description: str,
    date_incurred,
    amount_requested: Decimal,
) -> ExpenseLineItem:
    """
    Add an expense line item to a reimbursement request.

    Args:
        request: The reimbursement request
        category: One of ExpenseCategory choices
        description: Brief description of expense
        date_incurred: Date the expense occurred
        amount_requested: Amount in USD

    Returns:
        The created ExpenseLineItem

    Raises:
        StateTransitionError: If request is not editable
        ValidationError: If amount is invalid
    """
    if not request.is_editable:
        raise StateTransitionError(
            f"Cannot add expenses to a request in '{request.get_status_display()}' status."
        )

    if amount_requested <= 0:
        raise ValidationError("Amount must be greater than zero.")

    return ExpenseLineItem.objects.create(
        request=request,
        category=category,
        description=description,
        date_incurred=date_incurred,
        amount_requested=amount_requested,
    )


@transaction.atomic
def add_receipt(
    line_item: ExpenseLineItem,
    file,
    original_filename: str = "",
) -> Receipt:
    """
    Add a receipt to an expense line item.

    Args:
        line_item: The expense line item
        file: The uploaded file
        original_filename: Original filename (auto-detected if not provided)

    Returns:
        The created Receipt

    Raises:
        StateTransitionError: If request is not editable
    """
    if not line_item.request.is_editable:
        raise StateTransitionError("Cannot add receipts to a non-editable request.")

    return Receipt.objects.create(
        line_item=line_item,
        file=file,
        original_filename=original_filename or file.name,
        file_size=file.size,
    )


# =============================================================================
# STATE TRANSITIONS
# =============================================================================


@transaction.atomic
def submit_request(
    request: ReimbursementRequest,
    signature: str,
) -> ReimbursementRequest:
    """
    Submit a reimbursement request for review.

    Args:
        request: The request to submit
        signature: Digital signature (typed name)

    Returns:
        The submitted request

    Raises:
        ValidationError: If request is not ready for submission
        StateTransitionError: If transition is not allowed
    """
    # Validate signature
    if not signature:
        raise ValidationError("Signature is required.")

    request.signature = signature
    request.signed_at = timezone.now()

    # Validate has line items
    if not request.line_items.exists():
        raise ValidationError("At least one expense line item is required.")

    # Validate visa docs if required
    if request.requires_visa_docs and not request.passport_copy:
        raise ValidationError("Passport copy is required for visa holders.")

    # Attempt FSM transition
    if not request.can_submit():
        raise ValidationError("Request is not ready for submission.")

    request.submit()
    request.save()

    return request


@transaction.atomic
def request_changes(
    request: ReimbursementRequest,
    reviewer: User,
    notes: str,
) -> ReimbursementRequest:
    """
    Send a request back to the submitter for changes.

    Args:
        request: The request to send back
        reviewer: The staff user requesting changes
        notes: Explanation of what changes are needed

    Returns:
        The updated request

    Raises:
        StateTransitionError: If transition is not allowed
    """
    if request.status != RequestStatus.SUBMITTED:
        raise StateTransitionError("Can only request changes on submitted requests.")

    if not notes:
        raise ValidationError("Notes explaining required changes are required.")

    request.reviewed_by = reviewer
    request.request_changes(notes=notes)
    request.save()

    return request


@transaction.atomic
def approve_request(
    request: ReimbursementRequest,
    approver: User,
    approved_amounts: Optional[dict] = None,
) -> ReimbursementRequest:
    """
    Approve a reimbursement request for payment.

    Args:
        request: The request to approve
        approver: The staff user approving
        approved_amounts: Optional dict mapping line_item.id to approved amount.
                         If not provided, approved = requested for all items.

    Returns:
        The approved request

    Raises:
        StateTransitionError: If transition is not allowed
    """
    if request.status != RequestStatus.SUBMITTED:
        raise StateTransitionError("Can only approve submitted requests.")

    # Set approved amounts
    for item in request.line_items.all():
        if approved_amounts and item.id in approved_amounts:
            item.amount_approved = Decimal(str(approved_amounts[item.id]))
        else:
            item.amount_approved = item.amount_requested
        item.save()

    request.approved_by = approver
    request.approve()
    request.save()

    return request


@transaction.atomic
def mark_as_paid(
    request: ReimbursementRequest,
    paid_by: User,
    payment_reference: str = "",
    total_paid: Optional[Decimal] = None,
) -> ReimbursementRequest:
    """
    Mark a request as paid.

    Args:
        request: The request to mark as paid
        paid_by: The staff user processing payment
        payment_reference: Check number, wire reference, etc.
        total_paid: Actual amount paid (defaults to total_approved)

    Returns:
        The paid request

    Raises:
        StateTransitionError: If transition is not allowed
    """
    if request.status != RequestStatus.APPROVED:
        raise StateTransitionError("Can only mark approved requests as paid.")

    request.paid_by = paid_by
    request.mark_paid(payment_reference=payment_reference)

    if total_paid is not None:
        request.total_paid = total_paid

    request.save()

    return request


@transaction.atomic
def cancel_request(
    request: ReimbursementRequest,
    cancelled_by: User,
    reason: str = "",
) -> ReimbursementRequest:
    """
    Cancel a reimbursement request.

    Args:
        request: The request to cancel
        cancelled_by: The user cancelling
        reason: Reason for cancellation

    Returns:
        The cancelled request

    Raises:
        StateTransitionError: If request is already paid
    """
    if request.status == RequestStatus.PAID:
        raise StateTransitionError("Cannot cancel a paid request.")

    if request.status == RequestStatus.CANCELLED:
        raise StateTransitionError("Request is already cancelled.")

    request.cancelled_by = cancelled_by
    request.cancel(reason=reason)
    request.save()

    return request


# =============================================================================
# QUERY HELPERS
# =============================================================================


def get_user_requests(user: User):
    """Get all reimbursement requests submitted by a user."""
    return ReimbursementRequest.objects.for_user(user).select_related(
        "person",
        "enrollment__workshop",
    )


def get_person_requests(person: People):
    """Get all reimbursement requests for a person (as payee)."""
    return ReimbursementRequest.objects.for_person(person).select_related(
        "enrollment__workshop",
    )


def get_pending_review():
    """Get all requests awaiting review."""
    return ReimbursementRequest.objects.pending_review().select_related(
        "person",
        "enrollment__workshop",
        "submitted_by",
    ).prefetch_related("line_items")


def get_pending_payment():
    """Get all approved requests awaiting payment."""
    return ReimbursementRequest.objects.pending_payment().select_related(
        "person",
        "enrollment__workshop",
        "approved_by",
    )


def get_program_summary(program):
    """
    Get reimbursement summary for a program.

    Returns dict with:
        - total_requests: count of all requests
        - total_requested: sum of all requested amounts
        - total_approved: sum of approved amounts
        - total_paid: sum of paid amounts
        - by_status: breakdown by status
    """
    from django.db.models import Count, Sum

    requests = ReimbursementRequest.objects.for_program(program)

    totals = requests.aggregate(
        total_requested=Sum("total_requested"),
        total_approved=Sum("total_approved"),
        total_paid=Sum("total_paid"),
    )

    by_status = dict(
        requests.values("status").annotate(
            count=Count("id"),
            amount=Sum("total_requested"),
        ).values_list("status", "count")
    )

    return {
        "total_requests": requests.count(),
        "total_requested": totals["total_requested"] or Decimal("0.00"),
        "total_approved": totals["total_approved"] or Decimal("0.00"),
        "total_paid": totals["total_paid"] or Decimal("0.00"),
        "by_status": by_status,
    }
