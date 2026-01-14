from django.contrib import admin
from django.utils.html import format_html
from .models import People


@admin.register(People)
class PeopleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "full_name",
        "email_address",
        "institution",
        "orcid_link",
        "has_user_account",
        "enrollment_count",
        "created_at",
    )
    list_filter = ("created_at", "institution")
    search_fields = (
        "first_name",
        "last_name",
        "preferred_name",
        "email_address",
        "orcid_id",
        "institution",
    )
    readonly_fields = ("created_at", "updated_at", "enrollment_count")

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("first_name", "last_name", "preferred_name", "email_address")},
        ),
        (
            "Contact Information",
            {"fields": ("phone_number", "mailing_address", "institution")},
        ),
        (
            "Professional Information",
            {"fields": ("orcid_id", "home_page", "math_review_id")},
        ),
        (
            "Additional Information",
            {
                "fields": ("dietary_restrictions", "gender", "ethnicity"),
                "classes": ("collapse",),
            },
        ),
        ("Statistics", {"fields": ("enrollment_count",), "classes": ("collapse",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def full_name(self, obj):
        """Display full name in list view"""
        if obj.preferred_name:
            return f"{obj.preferred_name} {obj.last_name}"
        return f"{obj.first_name or ''} {obj.last_name or ''}".strip() or "—"

    full_name.short_description = "Name"
    full_name.admin_order_field = "last_name"

    def orcid_link(self, obj):
        """Display ORCID as clickable link"""
        if obj.orcid_id:
            url = f"https://orcid.org/{obj.orcid_id}"
            return format_html('<a href="{}" target="_blank">{}</a>', url, obj.orcid_id)
        return "—"

    orcid_link.short_description = "ORCID iD"

    def has_user_account(self, obj):
        """Check if person has a linked User account"""
        try:
            # UserProfile has a OneToOne relationship, not a reverse many
            has_account = hasattr(obj, "profile") and obj.profile is not None
            if has_account:
                return format_html('<span style="color: green;">✓</span>')
            return format_html('<span style="color: gray;">—</span>')
        except:
            return format_html('<span style="color: gray;">—</span>')

    has_user_account.short_description = "User Account"

    def enrollment_count(self, obj):
        """Count enrollments for this person"""
        count = obj.enrollments.count()
        return f"{count} program(s)"

    enrollment_count.short_description = "Enrollments"
