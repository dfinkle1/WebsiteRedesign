"""
Reimbursement Admin Configuration

Provides a comprehensive admin interface for managing reimbursement requests,
including workflow actions, bulk operations, and CSV export.
"""

import csv
from datetime import date
from decimal import Decimal

from django.contrib import admin, messages
from django.db.models import Sum
from django.http import HttpResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import (
    ReimbursementRequest,
    ExpenseLineItem,
    Receipt,
    RequestStatus,
)


# =============================================================================
# INLINES
# =============================================================================


class ReceiptInline(admin.TabularInline):
    """Inline for receipts within an expense line item."""

    model = Receipt
    extra = 0
    readonly_fields = ["file_size", "created_at"]
    fields = ["file", "original_filename", "file_size", "created_at"]


class ExpenseLineItemInline(admin.TabularInline):
    """Inline for expense line items within a reimbursement request."""

    model = ExpenseLineItem
    extra = 0
    fields = [
        "category",
        "description",
        "date_incurred",
        "amount_requested",
        "amount_approved",
        "reviewer_notes",
    ]
    readonly_fields = ["amount_requested"]

    def get_readonly_fields(self, request, obj=None):
        """Make all fields readonly if request is not in review."""
        if obj and obj.status not in [RequestStatus.DRAFT, RequestStatus.SUBMITTED]:
            return [f.name for f in self.model._meta.fields if f.name != "id"]
        return self.readonly_fields


# =============================================================================
# ADMIN ACTIONS
# =============================================================================


@admin.action(description="Approve selected requests")
def approve_requests(modeladmin, request, queryset):
    """Bulk approve submitted requests."""
    approved_count = 0
    for req in queryset.filter(status=RequestStatus.SUBMITTED):
        # Set approved amounts = requested amounts (can be modified individually)
        for item in req.line_items.all():
            if item.amount_approved is None:
                item.amount_approved = item.amount_requested
                item.save()
        req.approved_by = request.user
        req.approve()
        req.save()
        approved_count += 1

    if approved_count:
        messages.success(request, f"Approved {approved_count} request(s).")
    else:
        messages.warning(request, "No eligible requests to approve.")


@admin.action(description="Mark selected as paid")
def mark_as_paid(modeladmin, request, queryset):
    """Bulk mark approved requests as paid."""
    paid_count = 0
    for req in queryset.filter(status=RequestStatus.APPROVED):
        req.paid_by = request.user
        req.mark_paid()
        req.save()
        paid_count += 1

    if paid_count:
        messages.success(request, f"Marked {paid_count} request(s) as paid.")
    else:
        messages.warning(request, "No eligible requests to mark as paid.")


@admin.action(description="Export selected to CSV")
def export_to_csv(modeladmin, request, queryset):
    """Export selected requests to CSV for finance."""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="reimbursements_{date.today()}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "ID",
        "Status",
        "Person Name",
        "Person Email",
        "Program Code",
        "Program Title",
        "Total Requested",
        "Total Approved",
        "Total Paid",
        "Payment Method",
        "Payment Address",
        "Submitted At",
        "Approved At",
        "Approved By",
        "Paid At",
        "Payment Reference",
    ])

    for req in queryset.select_related(
        "person",
        "enrollment__workshop",
        "approved_by",
    ):
        program_code = ""
        program_title = ""
        if req.enrollment and req.enrollment.workshop:
            program_code = req.enrollment.workshop.code
            program_title = req.enrollment.workshop.title

        writer.writerow([
            req.id,
            req.get_status_display(),
            str(req.person),
            req.person.email_address,
            program_code,
            program_title,
            req.total_requested,
            req.total_approved or "",
            req.total_paid or "",
            req.get_payment_method_display(),
            req.payment_address.replace("\n", ", "),
            req.submitted_at.strftime("%Y-%m-%d %H:%M") if req.submitted_at else "",
            req.approved_at.strftime("%Y-%m-%d %H:%M") if req.approved_at else "",
            req.approved_by.get_full_name() if req.approved_by else "",
            req.paid_at.strftime("%Y-%m-%d %H:%M") if req.paid_at else "",
            req.payment_reference,
        ])

    return response


@admin.action(description="Export line items to CSV")
def export_line_items_to_csv(modeladmin, request, queryset):
    """Export line items from selected requests to CSV."""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="reimbursement_items_{date.today()}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "Request ID",
        "Person Name",
        "Program Code",
        "Category",
        "Description",
        "Date Incurred",
        "Amount Requested",
        "Amount Approved",
    ])

    for req in queryset.select_related("person", "enrollment__workshop").prefetch_related("line_items"):
        program_code = req.enrollment.workshop.code if req.enrollment and req.enrollment.workshop else ""
        for item in req.line_items.all():
            writer.writerow([
                req.id,
                str(req.person),
                program_code,
                item.get_category_display(),
                item.description,
                item.date_incurred,
                item.amount_requested,
                item.amount_approved or "",
            ])

    return response


# =============================================================================
# FILTERS
# =============================================================================


class ProgramFilter(admin.SimpleListFilter):
    """Filter requests by program."""

    title = "program"
    parameter_name = "program"

    def lookups(self, request, model_admin):
        # Get programs that have reimbursement requests
        from programs.models import Program

        programs = Program.objects.filter(
            enrollments__reimbursement_requests__isnull=False
        ).distinct().order_by("-start_date")[:20]
        return [(p.code, f"{p.code} - {p.title[:40]}") for p in programs]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(enrollment__workshop__code=self.value())
        return queryset


class HasEnrollmentFilter(admin.SimpleListFilter):
    """Filter by whether request is linked to enrollment."""

    title = "request type"
    parameter_name = "has_enrollment"

    def lookups(self, request, model_admin):
        return [
            ("yes", "Participant (with enrollment)"),
            ("no", "Staff/Vendor (no enrollment)"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(enrollment__isnull=False)
        if self.value() == "no":
            return queryset.filter(enrollment__isnull=True)
        return queryset


# =============================================================================
# MAIN ADMIN CLASS
# =============================================================================


@admin.register(ReimbursementRequest)
class ReimbursementRequestAdmin(admin.ModelAdmin):
    """Admin interface for reimbursement requests."""

    # -------------------------------------------------------------------------
    # LIST VIEW
    # -------------------------------------------------------------------------

    list_display = [
        "id",
        "status_badge",
        "person_link",
        "program_display",
        "total_requested",
        "total_approved_display",
        "submitted_at",
        "quick_actions",
    ]
    list_filter = [
        "status",
        ProgramFilter,
        HasEnrollmentFilter,
        "payment_method",
        "tax_status",
        ("submitted_at", admin.DateFieldListFilter),
    ]
    search_fields = [
        "person__first_name",
        "person__last_name",
        "person__email_address",
        "enrollment__workshop__title",
        "enrollment__workshop__code",
    ]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]

    # -------------------------------------------------------------------------
    # DETAIL VIEW
    # -------------------------------------------------------------------------

    inlines = [ExpenseLineItemInline]

    fieldsets = (
        (
            "Request Information",
            {
                "fields": (
                    "status",
                    "person",
                    "enrollment",
                    "submitted_by",
                ),
            },
        ),
        (
            "Financial Summary",
            {
                "fields": (
                    "total_requested",
                    "total_approved",
                    "total_paid",
                ),
            },
        ),
        (
            "Tax Information",
            {
                "fields": (
                    "tax_status",
                    "citizenship_country",
                    "visa_type",
                    "passport_number",
                    "passport_copy",
                    "us_entry_date",
                    "i94_document",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Payment Information",
            {
                "fields": (
                    "payment_method",
                    "payment_address",
                    "bank_name",
                    "bank_routing_number",
                    "bank_account_number",
                    "bank_account_type",
                ),
            },
        ),
        (
            "Signature",
            {
                "fields": (
                    "signature",
                    "signed_at",
                ),
            },
        ),
        (
            "Notes",
            {
                "fields": (
                    "submitter_notes",
                    "reviewer_notes",
                    "change_request_notes",
                ),
            },
        ),
        (
            "Audit Trail",
            {
                "fields": (
                    "submitted_at",
                    "reviewed_at",
                    "reviewed_by",
                    "approved_at",
                    "approved_by",
                    "paid_at",
                    "paid_by",
                    "payment_reference",
                    "cancelled_at",
                    "cancelled_by",
                    "cancellation_reason",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Snapshots (Frozen at Submission)",
            {
                "fields": (
                    "tax_info_snapshot",
                    "payment_info_snapshot",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    readonly_fields = [
        "status",
        "total_requested",
        "total_approved",
        "total_paid",
        "submitted_at",
        "reviewed_at",
        "reviewed_by",
        "approved_at",
        "approved_by",
        "paid_at",
        "paid_by",
        "cancelled_at",
        "cancelled_by",
        "tax_info_snapshot",
        "payment_info_snapshot",
    ]

    autocomplete_fields = ["person", "enrollment"]

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------

    actions = [approve_requests, mark_as_paid, export_to_csv, export_line_items_to_csv]

    # -------------------------------------------------------------------------
    # CUSTOM DISPLAY METHODS
    # -------------------------------------------------------------------------

    @admin.display(description="Status")
    def status_badge(self, obj):
        """Display status as colored badge."""
        colors = {
            RequestStatus.DRAFT: "#6c757d",  # gray
            RequestStatus.SUBMITTED: "#0d6efd",  # blue
            RequestStatus.CHANGES_NEEDED: "#ffc107",  # yellow
            RequestStatus.APPROVED: "#198754",  # green
            RequestStatus.PAID: "#20c997",  # teal
            RequestStatus.CANCELLED: "#dc3545",  # red
        }
        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display(),
        )

    @admin.display(description="Person")
    def person_link(self, obj):
        """Link to person in admin."""
        url = reverse("admin:people_people_change", args=[obj.person_id])
        return format_html('<a href="{}">{}</a>', url, obj.person)

    @admin.display(description="Program")
    def program_display(self, obj):
        """Display program code and title."""
        if obj.enrollment and obj.enrollment.workshop:
            return f"{obj.enrollment.workshop.code}"
        return "-"

    @admin.display(description="Approved")
    def total_approved_display(self, obj):
        """Display approved amount with formatting."""
        if obj.total_approved:
            return f"${obj.total_approved:,.2f}"
        return "-"

    @admin.display(description="Actions")
    def quick_actions(self, obj):
        """Quick action buttons in list view."""
        buttons = []

        if obj.status == RequestStatus.SUBMITTED:
            buttons.append(
                f'<a class="button" style="padding: 2px 8px; font-size: 11px;" '
                f'href="{reverse("admin:reimbursements_reimbursementrequest_change", args=[obj.pk])}'
                f'?_approve=1">Review</a>'
            )

        if obj.status == RequestStatus.APPROVED:
            buttons.append(
                f'<a class="button" style="padding: 2px 8px; font-size: 11px; '
                f'background: #198754; color: white;" '
                f'href="{reverse("admin:reimbursements_reimbursementrequest_change", args=[obj.pk])}'
                f'?_pay=1">Mark Paid</a>'
            )

        return format_html(" ".join(buttons)) if buttons else "-"

    # -------------------------------------------------------------------------
    # CUSTOM URLS
    # -------------------------------------------------------------------------

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "pending-review/",
                self.admin_site.admin_view(self.pending_review_view),
                name="reimbursements_pending_review",
            ),
            path(
                "pending-payment/",
                self.admin_site.admin_view(self.pending_payment_view),
                name="reimbursements_pending_payment",
            ),
        ]
        return custom_urls + urls

    def pending_review_view(self, request):
        """Redirect to filtered list of pending review requests."""
        return self.changelist_view(
            request,
            extra_context={"title": "Pending Review"},
        )

    def pending_payment_view(self, request):
        """Redirect to filtered list of pending payment requests."""
        return self.changelist_view(
            request,
            extra_context={"title": "Pending Payment"},
        )

    # -------------------------------------------------------------------------
    # PERMISSIONS
    # -------------------------------------------------------------------------

    def has_delete_permission(self, request, obj=None):
        """Only allow deletion of draft requests."""
        if obj and obj.status != RequestStatus.DRAFT:
            return False
        return super().has_delete_permission(request, obj)


# =============================================================================
# EXPENSE LINE ITEM ADMIN (for direct access)
# =============================================================================


@admin.register(ExpenseLineItem)
class ExpenseLineItemAdmin(admin.ModelAdmin):
    """Admin for expense line items (usually accessed via inline)."""

    list_display = [
        "id",
        "request_link",
        "category",
        "description",
        "date_incurred",
        "amount_requested",
        "amount_approved",
    ]
    list_filter = ["category", "date_incurred"]
    search_fields = ["description", "request__person__last_name"]
    inlines = [ReceiptInline]

    @admin.display(description="Request")
    def request_link(self, obj):
        url = reverse("admin:reimbursements_reimbursementrequest_change", args=[obj.request_id])
        return format_html('<a href="{}">#{}</a>', url, obj.request_id)


# =============================================================================
# RECEIPT ADMIN
# =============================================================================


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    """Admin for receipts (usually accessed via inline)."""

    list_display = ["id", "line_item", "original_filename", "file_size", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["original_filename"]
    readonly_fields = ["file_size", "created_at"]


