from django.contrib import admin
from django.utils.html import format_html
from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "event_type",
        "start",
        "status_badge",
        "location_display",
        "price_display",
        "capacity_display",
    ]
    list_filter = ["status", "event_type", "is_online", "is_free", "start"]
    search_fields = ["title", "short_summary", "venue_name", "city"]
    prepopulated_fields = {"slug": ["title"]}
    date_hierarchy = "start"
    ordering = ["-start"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            None,
            {
                "fields": ("title", "slug", "event_type", "status"),
            },
        ),
        (
            "Date & Time",
            {
                "fields": ("start", "end"),
            },
        ),
        (
            "Location",
            {
                "fields": (
                    "is_online",
                    "online_url",
                    "venue_name",
                    "address",
                    "city",
                    "region",
                    "country",
                ),
                "description": "For online events, provide the virtual meeting link. For in-person events, fill in the venue details.",
            },
        ),
        (
            "Content",
            {
                "fields": ("image", "short_summary", "description_html"),
            },
        ),
        (
            "Tickets & Registration",
            {
                "fields": (
                    "is_free",
                    "price",
                    "external_ticket_url",
                    "capacity",
                    "registration_required",
                ),
            },
        ),
        (
            "Metadata",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def status_badge(self, obj):
        colors = {
            "draft": "#6c757d",
            "published": "#28a745",
            "cancelled": "#dc3545",
            "postponed": "#ffc107",
        }
        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_badge.short_description = "Status"
    status_badge.admin_order_field = "status"

    def location_display(self, obj):
        if obj.is_online:
            return format_html('<span style="color: #0d6efd;">Online</span>')
        if obj.city:
            return f"{obj.city}, {obj.region}" if obj.region else obj.city
        return "-"

    location_display.short_description = "Location"

    def capacity_display(self, obj):
        if obj.capacity:
            return f"{obj.capacity}"
        return "Unlimited"

    capacity_display.short_description = "Capacity"

    def price_display(self, obj):
        return obj.price_display

    price_display.short_description = "Price"
