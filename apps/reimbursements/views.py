"""
Reimbursement Views

User-facing views for creating, editing, and viewing reimbursement requests.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, JsonResponse, FileResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, UpdateView

from .models import (
    ReimbursementRequest,
    ExpenseLineItem,
    Receipt,
    RequestStatus,
    TaxStatus,
)
from .forms import (
    ReimbursementCreateForm,
    ReimbursementEditForm,
    ExpenseLineItemForm,
    ReceiptUploadForm,
    SubmitSignatureForm,
)


class MyReimbursementsView(LoginRequiredMixin, ListView):
    """
    Dashboard showing all reimbursement requests for the logged-in user.
    """

    template_name = "reimbursements/my_reimbursements.html"
    context_object_name = "requests"
    login_url = "/accounts/login/"

    def get_queryset(self):
        return (
            ReimbursementRequest.objects.filter(submitted_by=self.request.user)
            .select_related("person", "enrollment__workshop", "approved_by")
            .prefetch_related("line_items")
            .order_by("-created_at")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        requests = self.get_queryset()
        context["summary"] = {
            "total": requests.count(),
            "draft": requests.filter(status=RequestStatus.DRAFT).count(),
            "submitted": requests.filter(status=RequestStatus.SUBMITTED).count(),
            "changes_needed": requests.filter(status=RequestStatus.CHANGES_NEEDED).count(),
            "approved": requests.filter(status=RequestStatus.APPROVED).count(),
            "paid": requests.filter(status=RequestStatus.PAID).count(),
        }
        return context


class ReimbursementDetailView(LoginRequiredMixin, DetailView):
    """
    Detail view for a single reimbursement request.
    """

    model = ReimbursementRequest
    template_name = "reimbursements/reimbursement_detail.html"
    context_object_name = "reimbursement"
    login_url = "/accounts/login/"

    def get_queryset(self):
        qs = ReimbursementRequest.objects.select_related(
            "person",
            "enrollment__workshop",
            "submitted_by",
            "approved_by",
            "paid_by",
        ).prefetch_related("line_items__receipts")

        if self.request.user.is_staff:
            return qs
        return qs.filter(submitted_by=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.object

        # Build status timeline
        context["timeline"] = []
        context["timeline"].append({
            "label": "Created",
            "date": obj.created_at,
            "completed": True,
        })

        if obj.submitted_at:
            context["timeline"].append({
                "label": "Submitted",
                "date": obj.submitted_at,
                "completed": True,
            })

        if obj.status == RequestStatus.CHANGES_NEEDED:
            context["timeline"].append({
                "label": "Changes Requested",
                "date": obj.reviewed_at,
                "completed": True,
                "notes": obj.change_request_notes,
            })

        if obj.approved_at:
            context["timeline"].append({
                "label": "Approved",
                "date": obj.approved_at,
                "completed": True,
                "user": obj.approved_by,
            })

        if obj.paid_at:
            context["timeline"].append({
                "label": "Paid",
                "date": obj.paid_at,
                "completed": True,
                "user": obj.paid_by,
                "notes": f"Reference: {obj.payment_reference}" if obj.payment_reference else None,
            })

        if obj.cancelled_at:
            context["timeline"].append({
                "label": "Cancelled",
                "date": obj.cancelled_at,
                "completed": True,
                "notes": obj.cancellation_reason,
            })

        return context


@login_required(login_url="/accounts/login/")
def reimbursement_status_check(request):
    """Simple status check page."""
    person = None
    try:
        if hasattr(request.user, "profile") and request.user.profile:
            person = request.user.profile.person
    except Exception:
        pass

    user_requests = ReimbursementRequest.objects.filter(
        submitted_by=request.user
    ).select_related("enrollment__workshop").order_by("-created_at")[:10]

    return render(request, "reimbursements/status_check.html", {
        "user_requests": user_requests,
        "person": person,
    })


# =============================================================================
# CREATE / EDIT FLOW
# =============================================================================


@login_required(login_url="/accounts/login/")
def reimbursement_create(request):
    """
    Create a new reimbursement request.

    The user must have a Person profile linked to submit reimbursements.
    """
    # Get the user's Person profile
    try:
        person = request.user.profile.person
    except AttributeError:
        messages.error(
            request,
            "Your account is not linked to a person record. Please contact support."
        )
        return redirect("reimbursements:my_reimbursements")

    if request.method == "POST":
        form = ReimbursementCreateForm(request.POST, person=person)
        if form.is_valid():
            reimbursement = form.save(commit=False)
            reimbursement.person = person
            reimbursement.submitted_by = request.user
            reimbursement.save()

            messages.success(request, "Reimbursement request created. Add your expenses below.")
            return redirect("reimbursements:edit", pk=reimbursement.pk)
    else:
        form = ReimbursementCreateForm(person=person)

    return render(request, "reimbursements/reimbursement_create.html", {
        "form": form,
        "person": person,
    })


@login_required(login_url="/accounts/login/")
def reimbursement_edit(request, pk):
    """
    Edit an existing draft/changes_needed reimbursement request.

    This is the main editing view where users add expenses and update info.
    """
    reimbursement = get_object_or_404(
        ReimbursementRequest.objects.select_related("person", "enrollment__workshop")
        .prefetch_related("line_items__receipts"),
        pk=pk
    )

    # Check ownership
    if reimbursement.submitted_by != request.user and not request.user.is_staff:
        raise Http404("Reimbursement not found")

    # Check if editable
    if not reimbursement.is_editable:
        messages.warning(request, "This reimbursement cannot be edited.")
        return redirect("reimbursements:detail", pk=pk)

    if request.method == "POST":
        form = ReimbursementEditForm(request.POST, request.FILES, instance=reimbursement)
        if form.is_valid():
            form.save()
            messages.success(request, "Changes saved.")
            return redirect("reimbursements:edit", pk=pk)
    else:
        form = ReimbursementEditForm(instance=reimbursement)

    expense_form = ExpenseLineItemForm()

    return render(request, "reimbursements/reimbursement_edit.html", {
        "reimbursement": reimbursement,
        "form": form,
        "expense_form": expense_form,
    })


@login_required(login_url="/accounts/login/")
def expense_add(request, pk):
    """Add an expense line item to a reimbursement."""
    reimbursement = get_object_or_404(ReimbursementRequest, pk=pk)

    if reimbursement.submitted_by != request.user and not request.user.is_staff:
        raise Http404()

    if not reimbursement.is_editable:
        messages.error(request, "Cannot add expenses to this reimbursement.")
        return redirect("reimbursements:edit", pk=pk)

    if request.method == "POST":
        form = ExpenseLineItemForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.request = reimbursement
            expense.save()
            messages.success(request, "Expense added.")

    return redirect("reimbursements:edit", pk=pk)


@login_required(login_url="/accounts/login/")
def expense_delete(request, pk, expense_pk):
    """Delete an expense line item."""
    reimbursement = get_object_or_404(ReimbursementRequest, pk=pk)

    if reimbursement.submitted_by != request.user and not request.user.is_staff:
        raise Http404()

    if not reimbursement.is_editable:
        messages.error(request, "Cannot modify this reimbursement.")
        return redirect("reimbursements:edit", pk=pk)

    expense = get_object_or_404(ExpenseLineItem, pk=expense_pk, request=reimbursement)

    if request.method == "POST":
        expense.delete()
        messages.success(request, "Expense removed.")

    return redirect("reimbursements:edit", pk=pk)


@login_required(login_url="/accounts/login/")
def receipt_upload(request, pk, expense_pk):
    """Upload a receipt for an expense line item."""
    reimbursement = get_object_or_404(ReimbursementRequest, pk=pk)

    if reimbursement.submitted_by != request.user and not request.user.is_staff:
        raise Http404()

    if not reimbursement.is_editable:
        messages.error(request, "Cannot modify this reimbursement.")
        return redirect("reimbursements:edit", pk=pk)

    expense = get_object_or_404(ExpenseLineItem, pk=expense_pk, request=reimbursement)

    if request.method == "POST" and request.FILES.get("file"):
        uploaded_file = request.FILES["file"]
        Receipt.objects.create(
            line_item=expense,
            file=uploaded_file,
            original_filename=uploaded_file.name,
            file_size=uploaded_file.size,
        )
        messages.success(request, "Receipt uploaded.")

    return redirect("reimbursements:edit", pk=pk)


@login_required(login_url="/accounts/login/")
def receipt_delete(request, pk, expense_pk, receipt_pk):
    """Delete a receipt."""
    reimbursement = get_object_or_404(ReimbursementRequest, pk=pk)

    if reimbursement.submitted_by != request.user and not request.user.is_staff:
        raise Http404()

    if not reimbursement.is_editable:
        messages.error(request, "Cannot modify this reimbursement.")
        return redirect("reimbursements:edit", pk=pk)

    receipt = get_object_or_404(
        Receipt,
        pk=receipt_pk,
        line_item__pk=expense_pk,
        line_item__request=reimbursement
    )

    if request.method == "POST":
        receipt.file.delete(save=False)
        receipt.delete()
        messages.success(request, "Receipt removed.")

    return redirect("reimbursements:edit", pk=pk)


@login_required(login_url="/accounts/login/")
def reimbursement_submit(request, pk):
    """
    Submit a reimbursement request for review.

    Validates all required fields and transitions to submitted status.
    """
    reimbursement = get_object_or_404(
        ReimbursementRequest.objects.prefetch_related("line_items"),
        pk=pk
    )

    if reimbursement.submitted_by != request.user and not request.user.is_staff:
        raise Http404()

    if not reimbursement.is_editable:
        messages.error(request, "This reimbursement has already been submitted.")
        return redirect("reimbursements:detail", pk=pk)

    # Validation errors to collect
    errors = []

    # Must have at least one expense
    if not reimbursement.line_items.exists():
        errors.append("You must add at least one expense.")

    # Check payment info
    if reimbursement.payment_method == "check" and not reimbursement.payment_address:
        errors.append("Mailing address is required for check payments.")
    elif reimbursement.payment_method == "ach":
        if not all([
            reimbursement.bank_name,
            reimbursement.bank_routing_number,
            reimbursement.bank_account_number
        ]):
            errors.append("Complete bank information is required for direct deposit.")

    # Check visa docs if needed
    if reimbursement.requires_visa_docs:
        if not reimbursement.citizenship_country:
            errors.append("Country of citizenship is required for visa holders.")
        if not reimbursement.visa_type:
            errors.append("Visa type is required for visa holders.")
        if not reimbursement.passport_copy:
            errors.append("Passport copy is required for visa holders.")

    if request.method == "POST":
        form = SubmitSignatureForm(request.POST)

        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect("reimbursements:edit", pk=pk)

        if form.is_valid():
            # Update signature
            reimbursement.signature = form.cleaned_data["signature"]
            reimbursement.signed_at = timezone.now()

            # Attempt FSM transition
            try:
                reimbursement.submit()
                reimbursement.save()
                messages.success(
                    request,
                    "Your reimbursement request has been submitted for review."
                )
                return redirect("reimbursements:detail", pk=pk)
            except Exception as e:
                messages.error(request, f"Could not submit: {e}")
                return redirect("reimbursements:edit", pk=pk)
    else:
        form = SubmitSignatureForm()

    return render(request, "reimbursements/reimbursement_submit.html", {
        "reimbursement": reimbursement,
        "form": form,
        "errors": errors,
    })


@login_required(login_url="/accounts/login/")
def reimbursement_cancel(request, pk):
    """Cancel a reimbursement request."""
    reimbursement = get_object_or_404(ReimbursementRequest, pk=pk)

    if reimbursement.submitted_by != request.user and not request.user.is_staff:
        raise Http404()

    if reimbursement.status == RequestStatus.PAID:
        messages.error(request, "Cannot cancel a paid reimbursement.")
        return redirect("reimbursements:detail", pk=pk)

    if reimbursement.status == RequestStatus.CANCELLED:
        messages.warning(request, "This reimbursement is already cancelled.")
        return redirect("reimbursements:detail", pk=pk)

    if request.method == "POST":
        reason = request.POST.get("reason", "Cancelled by user")
        try:
            reimbursement.cancel(reason=reason)
            reimbursement.cancelled_by = request.user
            reimbursement.save()
            messages.success(request, "Reimbursement request cancelled.")
        except Exception as e:
            messages.error(request, f"Could not cancel: {e}")

    return redirect("reimbursements:detail", pk=pk)


# =============================================================================
# PROTECTED FILE ACCESS
# =============================================================================


@login_required(login_url="/accounts/login/")
def protected_receipt(request, pk, expense_pk, receipt_pk):
    """
    Serve receipt files with authorization check.
    Only the submitter or staff can access receipt files.
    """
    reimbursement = get_object_or_404(ReimbursementRequest, pk=pk)

    # Authorization check
    if reimbursement.submitted_by != request.user and not request.user.is_staff:
        raise Http404("File not found")

    receipt = get_object_or_404(
        Receipt,
        pk=receipt_pk,
        line_item__pk=expense_pk,
        line_item__request=reimbursement,
    )

    # For S3 storage, redirect to a signed URL
    # For local storage, serve the file directly
    if hasattr(receipt.file.storage, 'url'):
        # S3 or other cloud storage - redirect to signed URL
        return HttpResponseRedirect(receipt.file.url)
    else:
        # Local filesystem - serve directly
        return FileResponse(
            receipt.file.open('rb'),
            as_attachment=False,
            filename=receipt.original_filename,
        )


@login_required(login_url="/accounts/login/")
def protected_visa_doc(request, pk, doc_type):
    """
    Serve visa documents (passport, i94) with authorization check.
    Only the submitter or staff can access these documents.
    """
    reimbursement = get_object_or_404(ReimbursementRequest, pk=pk)

    # Authorization check
    if reimbursement.submitted_by != request.user and not request.user.is_staff:
        raise Http404("File not found")

    # Get the appropriate file
    if doc_type == "passport" and reimbursement.passport_copy:
        file_field = reimbursement.passport_copy
    elif doc_type == "i94" and reimbursement.i94_document:
        file_field = reimbursement.i94_document
    else:
        raise Http404("File not found")

    # For S3 storage, redirect to a signed URL
    if hasattr(file_field.storage, 'url'):
        return HttpResponseRedirect(file_field.url)
    else:
        return FileResponse(
            file_field.open('rb'),
            as_attachment=False,
        )
