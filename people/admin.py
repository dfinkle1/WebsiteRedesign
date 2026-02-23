from django.contrib import admin
from django.utils.html import format_html
from .models import People
from enrollments.models import Enrollment


class EnrollmentInline(admin.TabularInline):
    """
    Inline display of enrollments on Person detail page.
    Shows all workshops this person has enrolled in.
    """

    model = Enrollment
    extra = 0  # Don't show empty forms by default
    can_delete = True

    # Use autocomplete for workshop field
    autocomplete_fields = ("workshop",)

    fields = (
        "workshop",
        "enrollment_status_display",
        "accepted_at",
        "declined_at",
        "declined_reason",
    )

    readonly_fields = ("enrollment_status_display",)

    verbose_name = "Workshop Enrollment"
    verbose_name_plural = "Workshop Enrollments"

    def enrollment_status_display(self, obj):
        """Show visual status indicator"""
        if not obj.pk:  # New unsaved enrollment
            return "—"

        if obj.accepted_at and obj.declined_at:
            return format_html(
                '<span style="color: orange;">⚠ Accepted→Declined</span>', "ok"
            )
        elif obj.accepted_at:
            return format_html('<span style="color: green;">✓ Accepted</span>', "ok")
        elif obj.declined_at:
            return format_html('<span style="color: red;">✗ Declined</span>', "ok")
        else:
            return format_html('<span style="color: gray;">— Pending</span>', "ok")

    enrollment_status_display.short_description = "Status"

    def get_queryset(self, request):
        """Optimize query with select_related, order by most recent first"""
        qs = super().get_queryset(request)
        return qs.select_related("workshop").order_by("-workshop__start_date")


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

    # Show enrollments inline on person detail page
    inlines = [EnrollmentInline]

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
            # Check if UserProfile exists (OneToOne relationship)
            if hasattr(obj, "user_profile") and obj.user_profile:
                username = obj.user_profile.user.username
                return format_html(
                    '<span style="color: green;" title="{}">✓</span>', username
                )
            return format_html('<span style="color: gray;">—</span>', "ok")
        except Exception:
            return format_html('<span style="color: gray;">—</span>', "ok")

    has_user_account.short_description = "User Account"

    def enrollment_count(self, obj):
        """Count enrollments for this person"""
        count = obj.enrollments.count()
        return f"{count} program(s)"

    enrollment_count.short_description = "Enrollments"
