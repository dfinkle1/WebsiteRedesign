"""
Reimbursement Admin Configuration

Staff-friendly interface for managing reimbursement requests with:
- Workflow action buttons (Approve, Request Changes, Mark Paid, Cancel)
- Multi-currency support with staff conversion
- Per diem and staff-added expense support
- Receipt visibility from the main request view
- CSV export for finance
"""

import csv
from datetime import date
from decimal import Decimal

from django.contrib import admin, messages
from django.db.models import Sum
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html, mark_safe

from .models import (
    ReimbursementRequest,
    ExpenseLineItem,
    Receipt,
    RequestStatus,
    Currency,
)


# =============================================================================
# INLINES
# =============================================================================


class ReceiptInline(admin.TabularInline):
    """Inline for receipts within an expense line item."""

    model = Receipt
    extra = 1
    readonly_fields = ["file_preview", "file_size", "created_at"]
    fields = ["file_preview", "file", "original_filename", "file_size", "created_at"]

    def file_preview(self, obj):
        """Show link to view/download the receipt."""
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank">View Receipt</a>',
                obj.file.url
            )
        return "-"
    file_preview.short_description = "Preview"


class ExpenseLineItemInline(admin.TabularInline):
    """
    Inline for expense line items within a reimbursement request.

    Staff can:
    - View participant-submitted expenses
    - Add new expenses like per diem (amount_requested editable)
    - Adjust amount_approved for any expense
    - Enter exchange rates for foreign currency expenses
    """

    model = ExpenseLineItem
    extra = 1  # Allow staff to add expenses (per diem, etc.)
    fields = [
        "category",
        "description",
        "date_incurred",
        "original_currency",
        "original_amount",
        "exchange_rate",
        "amount_requested",
        "amount_approved",
        "added_by_staff",
        "reviewer_notes",
    ]

    def get_readonly_fields(self, request, obj=None):
        """Lock fields for paid/cancelled requests."""
        if obj and obj.status in [RequestStatus.PAID, RequestStatus.CANCELLED]:
            return [f.name for f in self.model._meta.fields if f.name != "id"]
        return []

    def get_formset(self, request, obj=None, **kwargs):
        """Mark new items as staff-added."""
        formset = super().get_formset(request, obj, **kwargs)

        class StaffFormset(formset):
            def save_new(self, form, commit=True):
                instance = super().save_new(form, commit=False)
                instance.added_by_staff = True
                if commit:
                    instance.save()
                return instance

        return StaffFormset


# =============================================================================
# ADMIN ACTIONS
# =============================================================================


@admin.action(description="Approve selected requests (auto-fill amounts)")
def approve_requests(modeladmin, request, queryset):
    """Bulk approve submitted requests."""
    approved_count = 0
    for req in queryset.filter(status=RequestStatus.SUBMITTED):
        # Auto-fill approved amounts = requested amounts
        for item in req.line_items.all():
            if item.amount_approved is None:
                item.amount_approved = item.amount_requested
                item.save()
        req.approved_by = request.user
        req.approve()
        req.save()
        approved_count += 1

    if approved_count:
        messages.success(request, f"Approved {approved_count} request(s). Approved amounts set to requested amounts.")
    else:
        messages.warning(request, "No eligible requests to approve. Only 'Submitted' requests can be approved.")


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
        messages.warning(request, "No eligible requests. Only 'Approved' requests can be marked as paid.")


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
            req.person.email_address if req.person else "",
            program_code,
            program_title,
            req.total_requested,
            req.total_approved or "",
            req.total_paid or "",
            req.get_payment_method_display(),
            req.payment_address.replace("\n", ", ") if req.payment_address else "",
            req.submitted_at.strftime("%Y-%m-%d %H:%M") if req.submitted_at else "",
            req.approved_at.strftime("%Y-%m-%d %H:%M") if req.approved_at else "",
            req.approved_by.get_full_name() if req.approved_by else "",
            req.paid_at.strftime("%Y-%m-%d %H:%M") if req.paid_at else "",
            req.payment_reference,
        ])

    return response


@admin.action(description="Export line items to CSV (with currency)")
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
        "Original Currency",
        "Original Amount",
        "Exchange Rate",
        "Amount Requested (USD)",
        "Amount Approved (USD)",
        "Staff Added",
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
                item.original_currency,
                item.original_amount or "",
                item.exchange_rate or "",
                item.amount_requested,
                item.amount_approved or "",
                "Yes" if item.added_by_staff else "No",
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
        from programs.models import Program
        programs = Program.objects.filter(
            enrollments__reimbursement_requests__isnull=False
        ).distinct().order_by("-start_date")[:20]
        return [(p.code, f"{p.code} - {p.title[:40]}") for p in programs]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(enrollment__workshop__code=self.value())
        return queryset


class NeedsActionFilter(admin.SimpleListFilter):
    """Quick filter for requests needing staff action."""

    title = "needs action"
    parameter_name = "needs_action"

    def lookups(self, request, model_admin):
        return [
            ("review", "Needs Review"),
            ("payment", "Needs Payment"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "review":
            return queryset.filter(status=RequestStatus.SUBMITTED)
        if self.value() == "payment":
            return queryset.filter(status=RequestStatus.APPROVED)
        return queryset


class HasForeignCurrencyFilter(admin.SimpleListFilter):
    """Filter for requests with foreign currency expenses."""

    title = "currency"
    parameter_name = "currency"

    def lookups(self, request, model_admin):
        return [
            ("foreign", "Has Foreign Currency"),
            ("usd_only", "USD Only"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "foreign":
            return queryset.filter(line_items__original_currency__isnull=False).exclude(
                line_items__original_currency=Currency.USD
            ).distinct()
        if self.value() == "usd_only":
            return queryset.exclude(
                line_items__original_currency__isnull=False
            ).exclude(
                line_items__original_currency=Currency.USD
            ) | queryset.filter(line_items__original_currency=Currency.USD).distinct()
        return queryset


# =============================================================================
# MAIN ADMIN CLASS
# =============================================================================


@admin.register(ReimbursementRequest)
class ReimbursementRequestAdmin(admin.ModelAdmin):
    """
    Admin interface for reimbursement requests.

    Features:
    - Workflow buttons for Approve, Request Changes, Mark Paid, Cancel
    - Multi-currency support
    - Receipt visibility
    - Per diem / staff expense entry
    """

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
        NeedsActionFilter,
        "status",
        ProgramFilter,
        "payment_method",
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
            None,
            {
                "fields": (
                    "workflow_actions",
                    "status",
                    "person",
                    "enrollment",
                ),
            },
        ),
        (
            "Financial Summary",
            {
                "fields": (
                    "amounts_summary",
                ),
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
            "Signature",
            {
                "fields": (
                    "signature",
                    "signed_at",
                ),
                "classes": ("collapse",),
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
                    "submitted_by",
                    "submitted_at",
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
    )

    readonly_fields = [
        "workflow_actions",
        "amounts_summary",
        "status",
        "submitted_by",
        "submitted_at",
        "approved_at",
        "approved_by",
        "paid_at",
        "paid_by",
        "cancelled_at",
        "cancelled_by",
    ]

    autocomplete_fields = ["person", "enrollment"]

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------

    actions = [approve_requests, mark_as_paid, export_to_csv, export_line_items_to_csv]

    # -------------------------------------------------------------------------
    # WORKFLOW ACTION BUTTONS
    # -------------------------------------------------------------------------

    def workflow_actions(self, obj):
        """Display workflow action buttons based on current status."""
        if not obj.pk:
            return "Save the request first to see available actions."

        buttons = []

        if obj.status == RequestStatus.SUBMITTED:
            # Check if there are foreign currency items without conversion
            needs_conversion = obj.line_items.exclude(
                original_currency=Currency.USD
            ).filter(amount_requested__isnull=True).exists()

            if needs_conversion:
                buttons.append(
                    '<span style="background: #ffc107; color: black; padding: 8px 16px; '
                    'margin-right: 8px; border-radius: 4px;">'
                    'Foreign currency needs conversion before approval</span>'
                )

            buttons.append(
                f'<a class="button" style="background: #198754; color: white; '
                f'padding: 8px 16px; margin-right: 8px; text-decoration: none; border-radius: 4px;" '
                f'href="{reverse("admin:reimbursements_approve", args=[obj.pk])}">'
                f'Approve Request</a>'
            )
            buttons.append(
                f'<a class="button" style="background: #ffc107; color: black; '
                f'padding: 8px 16px; margin-right: 8px; text-decoration: none; border-radius: 4px;" '
                f'href="{reverse("admin:reimbursements_request_changes", args=[obj.pk])}">'
                f'Request Changes</a>'
            )

        elif obj.status == RequestStatus.APPROVED:
            buttons.append(
                f'<a class="button" style="background: #20c997; color: white; '
                f'padding: 8px 16px; margin-right: 8px; text-decoration: none; border-radius: 4px;" '
                f'href="{reverse("admin:reimbursements_mark_paid", args=[obj.pk])}">'
                f'Mark as Paid</a>'
            )

        if obj.status not in [RequestStatus.PAID, RequestStatus.CANCELLED]:
            buttons.append(
                f'<a class="button" style="background: #dc3545; color: white; '
                f'padding: 8px 16px; text-decoration: none; border-radius: 4px;" '
                f'href="{reverse("admin:reimbursements_cancel", args=[obj.pk])}">'
                f'Cancel Request</a>'
            )

        # PDF download button (for non-draft requests)
        if obj.status != RequestStatus.DRAFT:
            buttons.append(
                f'<a class="button" style="background: #6c757d; color: white; '
                f'padding: 8px 16px; margin-left: 15px; text-decoration: none; border-radius: 4px;" '
                f'href="{reverse("reimbursements:pdf", args=[obj.pk])}" target="_blank">'
                f'Download PDF</a>'
            )

        if not buttons:
            status_messages = {
                RequestStatus.DRAFT: "Waiting for participant to submit",
                RequestStatus.CHANGES_NEEDED: "Waiting for participant to resubmit",
                RequestStatus.PAID: "This request has been paid",
                RequestStatus.CANCELLED: "This request was cancelled",
            }
            msg = status_messages.get(obj.status, "")
            # For paid/cancelled, still show PDF button
            if obj.status in [RequestStatus.PAID, RequestStatus.CANCELLED]:
                return mark_safe(
                    f'<span style="color: #6c757d; font-style: italic; margin-right: 15px;">{msg}</span>'
                    f'<a class="button" style="background: #6c757d; color: white; '
                    f'padding: 8px 16px; text-decoration: none; border-radius: 4px;" '
                    f'href="{reverse("reimbursements:pdf", args=[obj.pk])}" target="_blank">'
                    f'Download PDF</a>'
                )
            return format_html(
                '<span style="color: #6c757d; font-style: italic;">{}</span>',
                msg
            )

        return mark_safe("".join(buttons))

    workflow_actions.short_description = "Workflow Actions"

    def amounts_summary(self, obj):
        """Display financial summary with currency info."""
        if not obj.pk:
            return "-"

        requested = obj.total_requested or Decimal("0.00")
        approved = obj.total_approved
        paid = obj.total_paid

        # Check for foreign currency items
        foreign_items = obj.line_items.exclude(original_currency=Currency.USD)

        html = '<div style="font-size: 14px; line-height: 1.8;">'
        html += f'<strong>Total Requested (USD):</strong> ${requested:,.2f}<br>'

        if approved is not None:
            color = "#198754" if approved == requested else "#ffc107"
            html += f'<strong>Total Approved:</strong> <span style="color: {color};">${approved:,.2f}</span><br>'
        else:
            html += '<strong>Total Approved:</strong> <span style="color: #6c757d;">Pending</span><br>'

        if paid is not None:
            html += f'<strong>Total Paid:</strong> <span style="color: #20c997;">${paid:,.2f}</span><br>'

        # Show foreign currency summary
        if foreign_items.exists():
            html += '<br><strong>Foreign Currency Items:</strong><ul style="margin: 4px 0; padding-left: 20px;">'
            for item in foreign_items:
                if item.original_amount:
                    html += f'<li>{item.original_currency} {item.original_amount:,.2f} '
                    if item.exchange_rate:
                        html += f'@ {item.exchange_rate} = ${item.amount_requested:,.2f}'
                    else:
                        html += '<span style="color: #dc3545;">(needs conversion)</span>'
                    html += f' - {item.description}</li>'
            html += '</ul>'

        html += '</div>'
        return mark_safe(html)

    amounts_summary.short_description = "Financial Summary"

    # -------------------------------------------------------------------------
    # CUSTOM DISPLAY METHODS
    # -------------------------------------------------------------------------

    @admin.display(description="Status")
    def status_badge(self, obj):
        """Display status as colored badge."""
        colors = {
            RequestStatus.DRAFT: "#6c757d",
            RequestStatus.SUBMITTED: "#0d6efd",
            RequestStatus.CHANGES_NEEDED: "#ffc107",
            RequestStatus.APPROVED: "#198754",
            RequestStatus.PAID: "#20c997",
            RequestStatus.CANCELLED: "#dc3545",
        }
        color = colors.get(obj.status, "#6c757d")
        text_color = "black" if obj.status == RequestStatus.CHANGES_NEEDED else "white"
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 3px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color,
            text_color,
            obj.get_status_display(),
        )

    @admin.display(description="Person")
    def person_link(self, obj):
        """Link to person in admin."""
        if not obj.person_id:
            return "-"
        url = reverse("admin:people_people_change", args=[obj.person_id])
        return format_html('<a href="{}">{}</a>', url, obj.person)

    @admin.display(description="Program")
    def program_display(self, obj):
        """Display program code."""
        if obj.enrollment and obj.enrollment.workshop:
            return f"{obj.enrollment.workshop.code}"
        return "-"

    @admin.display(description="Approved")
    def total_approved_display(self, obj):
        """Display approved amount."""
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
                f'href="{reverse("admin:reimbursements_reimbursementrequest_change", args=[obj.pk])}">'
                f'Review</a>'
            )

        if obj.status == RequestStatus.APPROVED:
            buttons.append(
                f'<a class="button" style="padding: 2px 8px; font-size: 11px; '
                f'background: #20c997; color: white;" '
                f'href="{reverse("admin:reimbursements_mark_paid", args=[obj.pk])}">'
                f'Pay</a>'
            )

        return mark_safe(" ".join(buttons)) if buttons else "-"

    # -------------------------------------------------------------------------
    # CUSTOM URLS FOR WORKFLOW ACTIONS
    # -------------------------------------------------------------------------

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:pk>/approve/",
                self.admin_site.admin_view(self.approve_view),
                name="reimbursements_approve",
            ),
            path(
                "<int:pk>/request-changes/",
                self.admin_site.admin_view(self.request_changes_view),
                name="reimbursements_request_changes",
            ),
            path(
                "<int:pk>/mark-paid/",
                self.admin_site.admin_view(self.mark_paid_view),
                name="reimbursements_mark_paid",
            ),
            path(
                "<int:pk>/cancel/",
                self.admin_site.admin_view(self.cancel_view),
                name="reimbursements_cancel",
            ),
        ]
        return custom_urls + urls

    def approve_view(self, request, pk):
        """Approve a single request."""
        obj = ReimbursementRequest.objects.get(pk=pk)

        if obj.status != RequestStatus.SUBMITTED:
            messages.error(request, f"Cannot approve - request is '{obj.get_status_display()}', not 'Submitted'.")
            return HttpResponseRedirect(reverse("admin:reimbursements_reimbursementrequest_change", args=[pk]))

        # Auto-fill approved amounts = requested amounts
        for item in obj.line_items.all():
            if item.amount_approved is None:
                item.amount_approved = item.amount_requested
                item.save()

        # Recalculate total
        obj.total_requested = obj.calculate_total_requested()

        obj.approved_by = request.user
        obj.approve()
        obj.save()

        messages.success(request, f"Request #{pk} approved! Total approved: ${obj.total_approved:,.2f}")
        return HttpResponseRedirect(reverse("admin:reimbursements_reimbursementrequest_changelist"))

    def request_changes_view(self, request, pk):
        """Send request back for changes."""
        obj = ReimbursementRequest.objects.get(pk=pk)

        if obj.status != RequestStatus.SUBMITTED:
            messages.error(request, f"Cannot request changes - request is '{obj.get_status_display()}'.")
            return HttpResponseRedirect(reverse("admin:reimbursements_reimbursementrequest_change", args=[pk]))

        obj.reviewed_by = request.user
        obj.request_changes(notes="Please review the notes and resubmit.")
        obj.save()

        messages.warning(request, f"Request #{pk} sent back for changes.")
        return HttpResponseRedirect(reverse("admin:reimbursements_reimbursementrequest_changelist"))

    def mark_paid_view(self, request, pk):
        """Mark request as paid."""
        obj = ReimbursementRequest.objects.get(pk=pk)

        if obj.status != RequestStatus.APPROVED:
            messages.error(request, f"Cannot mark as paid - request is '{obj.get_status_display()}', not 'Approved'.")
            return HttpResponseRedirect(reverse("admin:reimbursements_reimbursementrequest_change", args=[pk]))

        obj.paid_by = request.user
        obj.mark_paid()
        obj.save()

        messages.success(request, f"Request #{pk} marked as PAID! Total: ${obj.total_paid:,.2f}")
        return HttpResponseRedirect(reverse("admin:reimbursements_reimbursementrequest_changelist"))

    def cancel_view(self, request, pk):
        """Cancel a request."""
        obj = ReimbursementRequest.objects.get(pk=pk)

        if obj.status == RequestStatus.PAID:
            messages.error(request, "Cannot cancel a paid request.")
            return HttpResponseRedirect(reverse("admin:reimbursements_reimbursementrequest_change", args=[pk]))

        if obj.status == RequestStatus.CANCELLED:
            messages.warning(request, "Request is already cancelled.")
            return HttpResponseRedirect(reverse("admin:reimbursements_reimbursementrequest_change", args=[pk]))

        obj.cancelled_by = request.user
        obj.cancel(reason="Cancelled by staff.")
        obj.save()

        messages.warning(request, f"Request #{pk} has been cancelled.")
        return HttpResponseRedirect(reverse("admin:reimbursements_reimbursementrequest_changelist"))

    # -------------------------------------------------------------------------
    # SAVE HOOKS
    # -------------------------------------------------------------------------

    def save_related(self, request, form, formsets, change):
        """Recalculate totals after saving line items."""
        super().save_related(request, form, formsets, change)

        # Recalculate total_requested from line items
        obj = form.instance
        obj.total_requested = obj.calculate_total_requested()
        obj.save(update_fields=["total_requested"])

    # -------------------------------------------------------------------------
    # PERMISSIONS
    # -------------------------------------------------------------------------

    def has_delete_permission(self, request, obj=None):
        """Only allow deletion of draft requests."""
        if obj and obj.status != RequestStatus.DRAFT:
            return False
        return super().has_delete_permission(request, obj)


# =============================================================================
# EXPENSE LINE ITEM ADMIN
# =============================================================================


@admin.register(ExpenseLineItem)
class ExpenseLineItemAdmin(admin.ModelAdmin):
    """Admin for expense line items (usually accessed via inline)."""

    list_display = [
        "id",
        "request_link",
        "category",
        "description",
        "currency_amount",
        "amount_requested",
        "amount_approved",
        "receipt_count",
        "staff_added_badge",
    ]
    list_filter = ["category", "original_currency", "added_by_staff", "date_incurred"]
    search_fields = ["description", "request__person__last_name"]
    inlines = [ReceiptInline]

    @admin.display(description="Request")
    def request_link(self, obj):
        url = reverse("admin:reimbursements_reimbursementrequest_change", args=[obj.request_id])
        return format_html('<a href="{}">#{}</a>', url, obj.request_id)

    @admin.display(description="Original")
    def currency_amount(self, obj):
        if obj.original_currency != Currency.USD and obj.original_amount:
            return f"{obj.original_currency} {obj.original_amount:,.2f}"
        return "-"

    @admin.display(description="Receipts")
    def receipt_count(self, obj):
        count = obj.receipts.count()
        if count == 0:
            if obj.added_by_staff:
                return format_html('<span style="color: #6c757d;">N/A</span>')
            return format_html('<span style="color: #dc3545;">0</span>')
        return format_html('<span style="color: #198754;">{}</span>', count)

    @admin.display(description="Source")
    def staff_added_badge(self, obj):
        if obj.added_by_staff:
            return format_html(
                '<span style="background: #6c757d; color: white; padding: 2px 6px; '
                'border-radius: 3px; font-size: 10px;">STAFF</span>'
            )
        return ""


# =============================================================================
# RECEIPT ADMIN
# =============================================================================


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    """Admin for receipts."""

    list_display = ["id", "line_item", "original_filename", "file_size_display", "created_at", "file_link"]
    list_filter = ["created_at"]
    search_fields = ["original_filename"]
    readonly_fields = ["file_size", "created_at"]

    @admin.display(description="Size")
    def file_size_display(self, obj):
        if obj.file_size:
            if obj.file_size < 1024:
                return f"{obj.file_size} B"
            elif obj.file_size < 1024 * 1024:
                return f"{obj.file_size / 1024:.1f} KB"
            else:
                return f"{obj.file_size / (1024 * 1024):.1f} MB"
        return "-"

    @admin.display(description="View")
    def file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">View</a>', obj.file.url)
        return "-"
