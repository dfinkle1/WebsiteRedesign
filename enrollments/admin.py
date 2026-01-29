from django.contrib import admin
from django.utils.html import format_html
from .models import Enrollment


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    """
    Admin interface for Enrollment model.

    Uses autocomplete for person and workshop fields to handle 13k+ people efficiently.
    Search by ORCID, email, or name to find people quickly.
    """

    # Use autocomplete widgets instead of dropdowns (CRITICAL for 13k+ records)
    autocomplete_fields = ("person", "workshop")

    list_display = (
        "id",
        "person_link",
        "person_orcid",
        "workshop_link",
        "enrollment_status",
        "accepted_at",
        "declined_at",
        "created_at",
    )

    list_filter = (
        "workshop__type",
        "workshop__start_date",
        "accepted_at",
        "declined_at",
    )

    # Search across enrollment snapshot fields AND related person fields
    search_fields = (
        # Snapshot fields (from enrollment time)
        "first_name",
        "last_name",
        "email_snap",
        "orcid_snap",

        # Current person fields (from People table)
        "person__first_name",
        "person__last_name",
        "person__email_address",
        "person__orcid_id",

        # Workshop fields
        "workshop__title",
        "workshop__code",
    )

    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (
            "Person & Workshop",
            {
                "fields": ("person", "workshop"),
                "description": "Start typing name, ORCID, or email to search",
            },
        ),
        (
            "Snapshot Data (at enrollment time)",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "middle_name",
                    "email_snap",
                    "orcid_snap",
                    "institution",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Enrollment Status",
            {
                "fields": (
                    "accepted_at",
                    "declined_at",
                    "declined_reason",
                    "notes",
                )
            },
        ),
        (
            "Travel & Logistics",
            {
                "fields": (
                    "airport1",
                    "airport2",
                    "funding",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Contact Info",
            {
                "fields": (
                    "phone_number",
                    "mailing_address",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def person_link(self, obj):
        """Display person name with link to their detail page"""
        if obj.person:
            url = f"/admin/people/people/{obj.person.id}/change/"
            name = str(obj.person)
            return format_html('<a href="{}">{}</a>', url, name)
        return "—"

    person_link.short_description = "Person"
    person_link.admin_order_field = "person__last_name"

    def person_orcid(self, obj):
        """Display person's current ORCID"""
        if obj.person and obj.person.orcid_id:
            url = f"https://orcid.org/{obj.person.orcid_id}"
            return format_html('<a href="{}" target="_blank">{}</a>', url, obj.person.orcid_id)
        return "—"

    person_orcid.short_description = "ORCID"

    def workshop_link(self, obj):
        """Display workshop name with link"""
        if obj.workshop:
            url = f"/admin/programs/program/{obj.workshop.id}/change/"
            title = obj.workshop.title
            return format_html('<a href="{}">{}</a>', url, title)
        return "—"

    workshop_link.short_description = "Workshop"
    workshop_link.admin_order_field = "workshop__start_date"

    def enrollment_status(self, obj):
        """Visual indicator of enrollment status"""
        if obj.accepted_at and obj.declined_at:
            return format_html(
                '<span style="color: orange;">⚠ Accepted then Declined</span>'
            )
        elif obj.accepted_at:
            return format_html('<span style="color: green;">✓ Accepted</span>')
        elif obj.declined_at:
            return format_html('<span style="color: red;">✗ Declined</span>')
        else:
            return format_html('<span style="color: gray;">— Pending</span>')

    enrollment_status.short_description = "Status"
