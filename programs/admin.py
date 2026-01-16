from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from .models import Program
from enrollments.models import Enrollment


class EnrollmentInline(admin.TabularInline):
    """
    Inline display of enrollments on Program detail page.
    Shows all people enrolled in this workshop.
    """
    model = Enrollment
    extra = 0
    can_delete = True

    # Use autocomplete for person field
    autocomplete_fields = ("person",)

    fields = (
        "person",
        "person_email",
        "person_orcid",
        "enrollment_status_display",
        "accepted_at",
        "declined_at",
    )

    readonly_fields = (
        "person_email",
        "person_orcid",
        "enrollment_status_display",
    )

    def person_email(self, obj):
        """Show person's current email"""
        if obj.person:
            return obj.person.email_address or "—"
        return "—"

    person_email.short_description = "Email"

    def person_orcid(self, obj):
        """Show person's ORCID as link"""
        if obj.person and obj.person.orcid_id:
            url = f"https://orcid.org/{obj.person.orcid_id}"
            return format_html('<a href="{}" target="_blank">{}</a>', url, obj.person.orcid_id)
        return "—"

    person_orcid.short_description = "ORCID"

    def enrollment_status_display(self, obj):
        """Show visual status indicator"""
        if not obj.pk:
            return "—"

        if obj.accepted_at and obj.declined_at:
            return format_html('<span style="color: orange;">⚠</span>')
        elif obj.accepted_at:
            return format_html('<span style="color: green;">✓</span>')
        elif obj.declined_at:
            return format_html('<span style="color: red;">✗</span>')
        else:
            return format_html('<span style="color: gray;">—</span>')

    enrollment_status_display.short_description = "Status"

    def get_queryset(self, request):
        """Optimize query with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related("person").order_by("-accepted_at", "person__last_name")


class UpcomingFilter(admin.SimpleListFilter):
    title = "Date window"
    parameter_name = "when"

    def lookups(self, request, model_admin):
        return [("upcoming", "Upcoming"), ("past", "Past"), ("deadline", "Deadline")]

    def queryset(self, request, queryset):
        today = timezone.localdate()
        if self.value() == "upcoming":
            return queryset.filter(end_date__gte=today)
        if self.value() == "past":
            return queryset.filter(end_date__lt=today)
        if self.value() == "deadline":
            return queryset.filter(application_deadline__gte=today)
        return queryset


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "title",
        "type",
        "start_date",
        "end_date",
        "application_deadline",
        "enrollment_count",
    )
    list_filter = ("type", UpcomingFilter, "online")

    # Enhanced search - autocomplete will use these fields
    search_fields = (
        "code",
        "title",
        "abbreviation",
        "description",
        "organizer1",
        "organizer2",
    )

    ordering = ("-start_date",)  # Most recent first

    # Show enrollments inline on program detail page
    inlines = [EnrollmentInline]

    def enrollment_count(self, obj):
        """Show number of enrollments"""
        count = obj.enrollments.count()
        return f"{count} enrolled"

    enrollment_count.short_description = "Enrollments"
