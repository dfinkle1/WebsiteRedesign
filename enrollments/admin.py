from django.contrib import admin
from django.core.mail import send_mail
from django.conf import settings
from django.http import HttpResponseRedirect
from django.template.loader import render_to_string
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.contrib import messages
from django.shortcuts import render

from .models import Enrollment, ProgramInvitation, InvitationEmail


class PendingApplicationsFilter(admin.SimpleListFilter):
    """Filter for application status (pending/accepted/declined)."""

    title = "application status"
    parameter_name = "app_status"

    def lookups(self, request, model_admin):
        return [
            ("pending", "Pending Review"),
            ("accepted", "Accepted"),
            ("declined", "Declined"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "pending":
            return queryset.filter(accepted_at__isnull=True, declined_at__isnull=True)
        elif self.value() == "accepted":
            return queryset.filter(accepted_at__isnull=False)
        elif self.value() == "declined":
            return queryset.filter(declined_at__isnull=False)
        return queryset


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    """
    Admin interface for Enrollment model.

    Uses autocomplete for person and workshop fields to handle people efficiently.
    Search by ORCID, email, or name to find people quickly.
    """

    # Use autocomplete widgets instead of dropdowns
    autocomplete_fields = ("person", "workshop")

    list_display = (
        "id",
        "person_link",
        "workshop_link",
        "source",
        "enrollment_status",
        "created_at",
        "quick_actions",
    )

    ordering = ("-created_at",)

    list_filter = (
        PendingApplicationsFilter,
        "source",
        "workshop__type",
        "workshop__start_date",
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
                "fields": ("person", "workshop", "source"),
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
            "Lodging",
            {
                "fields": (
                    "check_in_date",
                    "check_out_date",
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
            return format_html(
                '<a href="{}" target="_blank">{}</a>', url, obj.person.orcid_id
            )
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

    actions = ["accept_applications", "decline_applications"]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "pending/",
                self.admin_site.admin_view(self.pending_applications_view),
                name="enrollments_enrollment_pending",
            ),
        ]
        return custom_urls + urls

    def pending_applications_view(self, request):
        """Redirect to filtered list showing only pending applications."""
        return HttpResponseRedirect(
            reverse("admin:enrollments_enrollment_changelist") + "?app_status=pending"
        )

    def changelist_view(self, request, extra_context=None):
        """Add pending count to changelist context."""
        extra_context = extra_context or {}
        extra_context["pending_count"] = Enrollment.objects.filter(
            accepted_at__isnull=True, declined_at__isnull=True
        ).count()
        return super().changelist_view(request, extra_context=extra_context)

    @admin.action(description="Accept selected applications")
    def accept_applications(self, request, queryset):
        """Bulk accept pending applications."""
        pending = queryset.filter(accepted_at__isnull=True, declined_at__isnull=True)
        count = pending.update(accepted_at=timezone.now())
        if count:
            messages.success(request, f"Accepted {count} application(s).")
        else:
            messages.warning(request, "No pending applications selected.")

    @admin.action(description="Decline selected applications")
    def decline_applications(self, request, queryset):
        """Bulk decline pending applications."""
        pending = queryset.filter(accepted_at__isnull=True, declined_at__isnull=True)
        count = pending.update(declined_at=timezone.now())
        if count:
            messages.success(request, f"Declined {count} application(s).")
        else:
            messages.warning(request, "No pending applications selected.")

    def enrollment_status(self, obj):
        """Visual indicator of enrollment status"""
        if obj.accepted_at and obj.declined_at:
            return format_html(
                '<span style="color: orange;">⚠ Accepted then Declined</span>', "yes"
            )
        elif obj.accepted_at:
            return format_html('<span style="color: green;">✓ Accepted</span>', "yes")
        elif obj.declined_at:
            return format_html('<span style="color: red;">✗ Declined</span>', "yes")
        else:
            return format_html('<span style="color: gray;">— Pending</span>', "yes")

    enrollment_status.short_description = "Status"

    def quick_actions(self, obj):
        """Quick action buttons for pending applications."""
        if obj.accepted_at or obj.declined_at:
            return "—"

        accept_url = reverse("admin:enrollments_enrollment_change", args=[obj.pk])
        return format_html(
            '<a class="button" style="padding: 2px 8px; font-size: 11px; background: #198754; color: white;" '
            'href="{}?_accept=1">Accept</a> '
            '<a class="button" style="padding: 2px 8px; font-size: 11px;" '
            'href="{}?_decline=1">Decline</a>',
            accept_url,
            accept_url,
        )

    quick_actions.short_description = "Actions"

    def change_view(self, request, object_id, form_url="", extra_context=None):
        """Handle quick accept/decline from list view."""
        if "_accept" in request.GET:
            obj = self.get_object(request, object_id)
            if obj and not obj.accepted_at and not obj.declined_at:
                obj.accepted_at = timezone.now()
                obj.save(update_fields=["accepted_at"])
                messages.success(request, f"Accepted application from {obj.person}.")
            return HttpResponseRedirect(
                request.META.get(
                    "HTTP_REFERER", reverse("admin:enrollments_enrollment_changelist")
                )
            )

        if "_decline" in request.GET:
            obj = self.get_object(request, object_id)
            if obj and not obj.accepted_at and not obj.declined_at:
                obj.declined_at = timezone.now()
                obj.save(update_fields=["declined_at"])
                messages.success(request, f"Declined application from {obj.person}.")
            return HttpResponseRedirect(
                request.META.get(
                    "HTTP_REFERER", reverse("admin:enrollments_enrollment_changelist")
                )
            )

        return super().change_view(request, object_id, form_url, extra_context)


class InvitationEmailInline(admin.TabularInline):
    """Inline display of emails sent for an invitation."""

    model = InvitationEmail
    extra = 0
    readonly_fields = ("sent_at", "sent_by", "subject", "body")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ProgramInvitation)
class ProgramInvitationAdmin(admin.ModelAdmin):
    """
    Admin interface for managing program invitations.

    Allows staff to create invitations and send invitation emails.
    """

    list_display = (
        "id",
        "email",
        "program_link",
        "status_badge",
        "person_link",
        "created_at",
        "emails_sent_count",
    )

    list_filter = (
        "status",
        "program",
        "created_at",
    )

    search_fields = (
        "email",
        "person__first_name",
        "person__last_name",
        "person__email_address",
        "program__title",
    )

    autocomplete_fields = ("person", "program")

    readonly_fields = (
        "token",
        "status",
        "enrollment",
        "created_at",
        "accepted_at",
        "declined_at",
        "invite_url",
    )

    inlines = [InvitationEmailInline]

    fieldsets = (
        (
            "Invitation Target",
            {
                "fields": ("program", "email", "person"),
                "description": "Email is required. Person is optional (will be linked when they accept).",
            },
        ),
        (
            "Invitation Message",
            {
                "fields": ("message",),
            },
        ),
        (
            "Status (Read Only)",
            {
                "fields": ("status", "token", "invite_url", "enrollment"),
                "classes": ("collapse",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "accepted_at", "declined_at", "invited_by"),
                "classes": ("collapse",),
            },
        ),
    )

    actions = ["send_invitation_email", "send_reminder_email"]

    def save_model(self, request, obj, form, change):
        if not change:  # New invitation
            obj.invited_by = request.user
        super().save_model(request, obj, form, change)

    def program_link(self, obj):
        if obj.program:
            url = f"/admin/programs/program/{obj.program.id}/change/"
            return format_html('<a href="{}">{}</a>', url, obj.program.title[:50])
        return "—"

    program_link.short_description = "Program"
    program_link.admin_order_field = "program__title"

    def person_link(self, obj):
        if obj.person:
            url = f"/admin/people/people/{obj.person.id}/change/"
            return format_html('<a href="{}">{}</a>', url, str(obj.person))
        return "—"

    person_link.short_description = "Person"

    def status_badge(self, obj):
        colors = {
            "pending": "orange",
            "accepted": "green",
            "declined": "gray",
        }
        color = colors.get(obj.status, "black")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_badge.short_description = "Status"
    status_badge.admin_order_field = "status"

    def emails_sent_count(self, obj):
        count = obj.emails.count()
        return count if count else "—"

    emails_sent_count.short_description = "Emails Sent"

    def invite_url(self, obj):
        if obj.token:
            url = reverse("enrollments:invitation_respond", args=[obj.token])
            full_url = (
                f"{settings.SITE_URL if hasattr(settings, 'SITE_URL') else ''}{url}"
            )
            return format_html(
                '<a href="{}" target="_blank">{}</a>', full_url, full_url
            )
        return "—"

    invite_url.short_description = "Invitation URL"

    @admin.action(description="Send invitation email to selected")
    def send_invitation_email(self, request, queryset):
        """Send initial invitation emails."""
        sent_count = 0
        for invitation in queryset.filter(status=ProgramInvitation.Status.PENDING):
            if self._send_email(request, invitation, is_reminder=False):
                sent_count += 1

        if sent_count:
            messages.success(request, f"Sent {sent_count} invitation email(s).")
        else:
            messages.warning(
                request, "No emails sent. Check that invitations are pending."
            )

    @admin.action(description="Send reminder email to selected")
    def send_reminder_email(self, request, queryset):
        """Send reminder emails to pending invitations that have already received at least one email."""
        sent_count = 0
        for invitation in queryset.filter(status=ProgramInvitation.Status.PENDING):
            if invitation.emails.exists() and self._send_email(
                request, invitation, is_reminder=True
            ):
                sent_count += 1

        if sent_count:
            messages.success(request, f"Sent {sent_count} reminder email(s).")
        else:
            messages.warning(
                request,
                "No reminders sent. Invitations must be pending and have received a prior email.",
            )

    def _send_email(self, request, invitation, is_reminder=False):
        """Send an invitation or reminder email."""
        if invitation.is_expired:
            return False

        invite_url = request.build_absolute_uri(
            reverse("enrollments:invitation_respond", args=[invitation.token])
        )

        subject_prefix = "Reminder: " if is_reminder else ""
        subject = f"{subject_prefix}You're invited to {invitation.program.title}"

        body = f"""
You have been invited to participate in {invitation.program.title}.

Program Dates: {invitation.program.start_date} - {invitation.program.end_date}
Location: {invitation.program.location or 'TBD'}

Please respond by: {invitation.expires_at}

{invitation.message if invitation.message else ''}

To accept or decline this invitation, please visit:
{invite_url}

If you have any questions, please contact workshops@aimath.org.

Best regards,
American Institute of Mathematics
        """.strip()

        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[invitation.email],
                fail_silently=False,
            )

            # Record the email
            InvitationEmail.objects.create(
                invitation=invitation,
                sent_by=request.user,
                subject=subject,
                body=body,
            )

            return True
        except Exception as e:
            messages.error(request, f"Failed to send email to {invitation.email}: {e}")
            return False
