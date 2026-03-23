import csv

from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import format_html

from .models import Donation, DonationCategory, OrganizationSettings, WebhookEvent
from .services.emails import send_receipt_email
from .services.paypal import refund_capture

STATUS_COLORS = {
    "pending": "#f59e0b",
    "completed": "#16a34a",
    "failed": "#dc2626",
    "refunded": "#6b7280",
    "cancelled": "#9ca3af",
}


@admin.register(DonationCategory)
class DonationCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active", "sort_order"]
    prepopulated_fields = {"slug": ["name"]}


@admin.register(OrganizationSettings)
class OrganizationSettingsAdmin(admin.ModelAdmin):
    """Prevent creating a second row or deleting the only row."""

    def has_add_permission(self, request):
        return not OrganizationSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = [
        "donor_name",
        "donor_email",
        "amount",
        "category",
        "colored_status",
        "receipt_number",
        "receipt_sent_at",
        "created_at",
    ]
    list_filter = ["status", "category", "created_at"]
    search_fields = ["donor_name", "donor_email", "receipt_number", "paypal_order_id"]
    readonly_fields = [
        "paypal_order_id",
        "paypal_capture_id",
        "receipt_number",
        "receipt_sent_at",
        "completed_at",
        "ip_address",
        "created_at",
        "updated_at",
    ]
    actions = ["resend_receipt", "export_csv", "process_refund"]

    @admin.display(description="Status")
    def colored_status(self, obj):
        color = STATUS_COLORS.get(obj.status, "#000")
        return format_html(
            '<span style="color:{};font-weight:bold;">{}</span>',
            color,
            obj.get_status_display(),
        )

    # -----------------------------------------------------------------------
    # Action: resend receipt
    # -----------------------------------------------------------------------
    @admin.action(description="Resend receipt email to selected donors")
    def resend_receipt(self, request, queryset):
        sent = 0
        skipped = 0
        for donation in queryset:
            if donation.status != Donation.Status.COMPLETED:
                skipped += 1
                continue
            if send_receipt_email(donation):
                sent += 1
        msg = f"Sent {sent} receipt(s)."
        if skipped:
            msg += f" Skipped {skipped} (not completed)."
        self.message_user(request, msg)

    # -----------------------------------------------------------------------
    # Action: export CSV
    # -----------------------------------------------------------------------
    @admin.action(description="Export selected donations to CSV")
    def export_csv(self, request, queryset):
        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="donations_{timestamp}.csv"'

        writer = csv.writer(response)
        writer.writerow([
            "Receipt Number",
            "Date",
            "Donor Name",
            "Donor Email",
            "Amount",
            "Currency",
            "Fund",
            "Status",
            "PayPal Order ID",
            "PayPal Capture ID",
            "Goods/Services Provided",
            "Receipt Sent At",
        ])

        for d in queryset.select_related("category").order_by("-created_at"):
            writer.writerow([
                d.receipt_number or "",
                d.completed_at.strftime("%Y-%m-%d") if d.completed_at else d.created_at.strftime("%Y-%m-%d"),
                d.donor_name,
                d.donor_email,
                d.amount,
                d.currency,
                d.category.name,
                d.get_status_display(),
                d.paypal_order_id,
                d.paypal_capture_id,
                "Yes" if d.goods_or_services_provided else "No",
                d.receipt_sent_at.strftime("%Y-%m-%d %H:%M") if d.receipt_sent_at else "",
            ])

        return response

    # -----------------------------------------------------------------------
    # Action: process refund
    # -----------------------------------------------------------------------
    @admin.action(description="Process full refund via PayPal for selected donations")
    def process_refund(self, request, queryset):
        """
        Calls PayPal's refund API for each selected completed donation,
        then marks it as refunded in the database.

        Only works on completed donations that have a paypal_capture_id.
        Skips anything already refunded, pending, failed, or cancelled.
        """
        refunded = 0
        skipped = 0
        errors = 0

        for donation in queryset:
            if donation.status != Donation.Status.COMPLETED:
                skipped += 1
                continue

            if not donation.paypal_capture_id:
                self.message_user(
                    request,
                    f"Donation {donation.pk} ({donation.donor_name}) has no PayPal capture ID — skipped.",
                    level="warning",
                )
                skipped += 1
                continue

            try:
                refund_capture(donation.paypal_capture_id)
                Donation.objects.filter(pk=donation.pk).update(
                    status=Donation.Status.REFUNDED,
                )
                refunded += 1
            except Exception as exc:
                self.message_user(
                    request,
                    f"Refund failed for {donation.donor_name} (${donation.amount}): {exc}",
                    level="error",
                )
                errors += 1

        parts = []
        if refunded:
            parts.append(f"{refunded} donation(s) refunded successfully.")
        if skipped:
            parts.append(f"{skipped} skipped (not completed or missing capture ID).")
        if errors:
            parts.append(f"{errors} failed — see errors above.")
        if parts:
            self.message_user(request, " ".join(parts))


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ["event_type", "paypal_event_id", "processed", "received_at", "has_error"]
    list_filter = ["event_type", "processed"]
    readonly_fields = ["paypal_event_id", "event_type", "raw_body", "received_at", "processed", "error"]

    @admin.display(boolean=True, description="Error?")
    def has_error(self, obj):
        return bool(obj.error)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
