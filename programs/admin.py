from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from datetime import datetime
from cms.admin.placeholderadmin import FrontendEditableAdminMixin
import csv

from .models import Program, Workshop, SQuaRE, ResearchCommunity
from enrollments.models import Enrollment, ProgramInvitation, InvitationEmail
from .forms import SendReminderForm, BulkInviteForm


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
            return format_html(
                '<a href="{}" target="_blank">{}</a>', url, obj.person.orcid_id
            )
        return "—"

    person_orcid.short_description = "ORCID"

    def enrollment_status_display(self, obj):
        """Show visual status indicator"""
        if not obj or not obj.pk:
            return "—"

        if obj.accepted_at and obj.declined_at:
            return "⚠️ Withdrawn"
        elif obj.accepted_at:
            return "✅ Accepted"
        elif obj.declined_at:
            return "❌ Declined"
        else:
            return "⏳ Pending"

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
class ProgramAdmin(FrontendEditableAdminMixin, admin.ModelAdmin):

    list_display = (
        "code",
        "short_title",
        "type",
        "dates_display",
        "enrollment_count",
        "quick_actions",
    )
    frontend_editable_fields = ("code", "title")

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

    # Bulk actions
    actions = ["export_programs_csv", "export_bulk_name_badges"]

    def get_urls(self):
        """Add custom URLs for staff tools"""
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:program_id>/applicants/",
                self.admin_site.admin_view(self.applicants_view),
                name="programs_program_applicants",
            ),
            path(
                "<int:program_id>/export-csv/",
                self.admin_site.admin_view(self.export_applicants_csv),
                name="programs_program_export_csv",
            ),
            path(
                "<int:program_id>/emails/",
                self.admin_site.admin_view(self.get_emails_view),
                name="programs_program_emails",
            ),
            path(
                "<int:program_id>/send-reminder/",
                self.admin_site.admin_view(self.send_reminder_view),
                name="programs_program_send_reminder",
            ),
            path(
                "<int:program_id>/bulk-invite/",
                self.admin_site.admin_view(self.bulk_invite_view),
                name="programs_program_bulk_invite",
            ),
            path(
                "<int:program_id>/name-badges/",
                self.admin_site.admin_view(self.export_name_badges),
                name="programs_program_name_badges",
            ),
        ]
        return custom_urls + urls

    def short_title(self, obj):
        """Truncated title with tooltip for full text"""
        max_len = 50
        if len(obj.title) > max_len:
            return format_html(
                '<span title="{}">{}&hellip;</span>', obj.title, obj.title[:max_len]
            )
        return obj.title

    short_title.short_description = "Title"
    short_title.admin_order_field = "title"

    def dates_display(self, obj):
        """Compact date range display"""
        if obj.start_date and obj.end_date:
            # Same year? Show compact format
            if obj.start_date.year == obj.end_date.year:
                return format_html(
                    '<span style="white-space:nowrap">{} - {}</span>',
                    obj.start_date.strftime("%b %d"),
                    obj.end_date.strftime("%b %d, %Y"),
                )
            return format_html(
                '<span style="white-space:nowrap">{} - {}</span>',
                obj.start_date.strftime("%b %d, %Y"),
                obj.end_date.strftime("%b %d, %Y"),
            )
        return "—"

    dates_display.short_description = "Dates"
    dates_display.admin_order_field = "start_date"

    def enrollment_count(self, obj):
        """Show number of enrollments"""
        count = obj.enrollments.count()
        return count

    enrollment_count.short_description = "#"

    def quick_actions(self, obj):
        """Compact action links with icons"""
        applicants_url = reverse("admin:programs_program_applicants", args=[obj.id])
        export_url = reverse("admin:programs_program_export_csv", args=[obj.id])
        emails_url = reverse("admin:programs_program_emails", args=[obj.id])
        invite_url = reverse("admin:programs_program_bulk_invite", args=[obj.id])
        badges_url = reverse("admin:programs_program_name_badges", args=[obj.id])

        return format_html(
            '<a href="{}">👥 Applicants</a> | '
            '<a href="{}">📥 CSV</a> | '
            '<a href="{}">📧 Emails</a> | '
            '<a href="{}">✉️ Invite</a> | '
            '<a href="{}">🏷️ Badges</a>',
            applicants_url,
            export_url,
            emails_url,
            invite_url,
            badges_url,
        )

    quick_actions.short_description = "Actions"

    # Keep old staff_actions for detail page if needed
    def staff_actions(self, obj):
        """Action buttons for each program"""
        applicants_url = reverse("admin:programs_program_applicants", args=[obj.id])
        export_url = reverse("admin:programs_program_export_csv", args=[obj.id])
        emails_url = reverse("admin:programs_program_emails", args=[obj.id])
        reminder_url = reverse("admin:programs_program_send_reminder", args=[obj.id])
        invite_url = reverse("admin:programs_program_bulk_invite", args=[obj.id])

        return format_html(
            '<a class="button" href="{}" style="padding: 5px 10px; margin: 2px;">👥 Applicants</a> '
            '<a class="button" href="{}" style="padding: 5px 10px; margin: 2px;">📥 CSV</a> '
            '<a class="button" href="{}" style="padding: 5px 10px; margin: 2px;">📧 Emails</a> '
            '<a class="button" href="{}" style="padding: 5px 10px; margin: 2px;">📬 Remind</a> '
            '<a class="button" href="{}" style="padding: 5px 10px; margin: 2px; background: #417690; color: white;">✉️ Bulk Invite</a>',
            applicants_url,
            export_url,
            emails_url,
            reminder_url,
            invite_url,
        )

    staff_actions.short_description = "Staff Tools"

    # ========== CUSTOM VIEWS ==========

    def applicants_view(self, request, program_id):
        """View all applicants for a program"""
        program = get_object_or_404(Program, id=program_id)

        if not self.has_view_permission(request, program):
            return HttpResponse("Permission denied", status=403)

        enrollments = (
            Enrollment.objects.filter(workshop=program)
            .select_related("person")
            .order_by("-accepted_at", "person__last_name", "person__first_name")
        )

        # Compute stats
        stats = {
            "total": enrollments.count(),
            "accepted": enrollments.filter(accepted_at__isnull=False).count(),
            "declined": enrollments.filter(declined_at__isnull=False).count(),
            "pending": enrollments.filter(
                accepted_at__isnull=True, declined_at__isnull=True
            ).count(),
        }

        context = {
            **self.admin_site.each_context(request),
            "program": program,
            "enrollments": enrollments,
            "stats": stats,
            "title": f"Applicants for {program.title}",
        }

        return render(request, "admin/programs/applicants.html", context)

    def export_applicants_csv(self, request, program_id):
        """Export applicants to CSV"""
        program = get_object_or_404(Program, id=program_id)

        if not self.has_view_permission(request, program):
            return HttpResponse("Permission denied", status=403)

        enrollments = (
            Enrollment.objects.filter(workshop=program)
            .select_related("person")
            .order_by("person__last_name", "person__first_name")
        )

        # Create CSV response
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="program_{program.code}_applicants_'
            f'{datetime.now().strftime("%Y%m%d")}.csv"'
        )

        writer = csv.writer(response)
        writer.writerow(
            [
                "Last Name",
                "First Name",
                "Email",
                "ORCID",
                "Institution",
                "Status",
                "Accepted At",
                "Declined At",
            ]
        )

        for enrollment in enrollments:
            person = enrollment.person
            if enrollment.accepted_at:
                status = "Accepted"
            elif enrollment.declined_at:
                status = "Declined"
            else:
                status = "Pending"

            writer.writerow(
                [
                    person.last_name or "",
                    person.first_name or "",
                    person.email_address or "",
                    person.orcid_id or "",
                    person.institution or "",
                    status,
                    (
                        enrollment.accepted_at.strftime("%Y-%m-%d %H:%M")
                        if enrollment.accepted_at
                        else ""
                    ),
                    (
                        enrollment.declined_at.strftime("%Y-%m-%d %H:%M")
                        if enrollment.declined_at
                        else ""
                    ),
                ]
            )

        # Log the export
        self.log_change(
            request, program, f"Exported {enrollments.count()} applicants to CSV"
        )

        return response

    def get_emails_view(self, request, program_id):
        """Show comma-separated emails"""
        program = get_object_or_404(Program, id=program_id)

        if not self.has_view_permission(request, program):
            return HttpResponse("Permission denied", status=403)

        # Get accepted applicants' emails (deduplicated)
        emails = (
            Enrollment.objects.filter(
                workshop=program,
                accepted_at__isnull=False,
                person__email_address__isnull=False,
            )
            .values_list("person__email_address", flat=True)
            .distinct()
        )

        emails_list = sorted(list(emails))
        emails_str = ", ".join(emails_list)

        context = {
            **self.admin_site.each_context(request),
            "program": program,
            "emails": emails_list,
            "emails_str": emails_str,
            "count": len(emails_list),
            "title": f"Emails for {program.title}",
        }

        return render(request, "admin/programs/emails.html", context)

    def send_reminder_view(self, request, program_id):
        """Send reminder with confirmation"""
        program = get_object_or_404(Program, id=program_id)

        if not self.has_change_permission(request, program):
            return HttpResponse("Permission denied", status=403)

        # Get pending applicants
        pending = Enrollment.objects.filter(
            workshop=program,
            accepted_at__isnull=True,
            declined_at__isnull=True,
            person__email_address__isnull=False,
        ).select_related("person")

        if request.method == "POST":
            form = SendReminderForm(request.POST)

            if form.is_valid() and form.cleaned_data.get("confirm"):
                # Send emails (placeholder - will use Django's email backend)
                sent_count = 0
                errors = []

                for enrollment in pending:
                    try:
                        self._send_reminder_email(
                            enrollment.person.email_address,
                            program,
                            form.cleaned_data["message"],
                        )
                        sent_count += 1
                    except Exception as e:
                        errors.append(f"{enrollment.person.email_address}: {str(e)}")

                # Log the action
                self.log_change(
                    request,
                    program,
                    f"Sent reminder to {sent_count} applicants by {request.user.username}",
                )

                if errors:
                    messages.warning(
                        request,
                        f"Sent {sent_count} emails with {len(errors)} errors: {', '.join(errors[:3])}",
                    )
                else:
                    messages.success(
                        request, f"Successfully sent {sent_count} reminder emails"
                    )

                return redirect("admin:programs_program_change", program.id)
        else:
            form = SendReminderForm(
                initial={
                    "message": f"Reminder: Please respond to your application for {program.title}"
                }
            )

        context = {
            **self.admin_site.each_context(request),
            "program": program,
            "pending": pending,
            "count": pending.count(),
            "form": form,
            "title": f"Send Reminder - {program.title}",
        }

        return render(request, "admin/programs/send_reminder.html", context)

    def _send_reminder_email(self, email, program, message):
        """Send reminder email using Django's email backend"""
        from django.core.mail import send_mail

        send_mail(
            subject=f"Reminder: {program.title}",
            message=message,
            from_email="noreply@example.com",  # Update with your from email
            recipient_list=[email],
            fail_silently=False,
        )

    def bulk_invite_view(self, request, program_id):
        """Bulk invite participants by email addresses."""
        from django.core.mail import send_mail
        from django.conf import settings
        from people.models import People

        program = get_object_or_404(Program, id=program_id)

        if not self.has_change_permission(request, program):
            return HttpResponse("Permission denied", status=403)

        # Get existing invitations and enrollments for this program
        existing_invite_emails = set(
            ProgramInvitation.objects.filter(program=program).values_list(
                "email", flat=True
            )
        )
        existing_enrollment_emails = set(
            Enrollment.objects.filter(
                workshop=program, person__email_address__isnull=False
            ).values_list("person__email_address", flat=True)
        )

        if request.method == "POST":
            form = BulkInviteForm(request.POST)

            if form.is_valid():
                emails = form.cleaned_data["emails"]
                message = form.cleaned_data.get("message", "")
                send_emails = form.cleaned_data.get("send_emails", True)

                created_count = 0
                skipped_existing = []
                skipped_enrolled = []
                email_errors = []

                for email in emails:
                    email_lower = email.lower()

                    # Skip if already invited
                    if email_lower in existing_invite_emails:
                        skipped_existing.append(email)
                        continue

                    # Skip if already enrolled
                    if email_lower in existing_enrollment_emails:
                        skipped_enrolled.append(email)
                        continue

                    # Try to find existing person by email
                    person = People.objects.filter(email_address__iexact=email).first()

                    # Create invitation
                    invitation = ProgramInvitation.objects.create(
                        program=program,
                        email=email_lower,
                        person=person,
                        message=message,
                        invited_by=request.user,
                    )
                    created_count += 1
                    existing_invite_emails.add(email_lower)  # Track for deduplication

                    # Send email if requested
                    if send_emails:
                        try:
                            self._send_invitation_email(request, invitation)
                        except Exception as e:
                            email_errors.append(f"{email}: {str(e)}")

                # Build result message
                result_parts = []
                if created_count:
                    result_parts.append(f"Created {created_count} invitation(s)")
                if skipped_existing:
                    result_parts.append(
                        f"Skipped {len(skipped_existing)} already invited"
                    )
                if skipped_enrolled:
                    result_parts.append(
                        f"Skipped {len(skipped_enrolled)} already enrolled"
                    )

                if result_parts:
                    messages.success(request, ". ".join(result_parts) + ".")

                if email_errors:
                    messages.warning(
                        request,
                        f"Email errors: {', '.join(email_errors[:3])}"
                        + (
                            f" and {len(email_errors) - 3} more"
                            if len(email_errors) > 3
                            else ""
                        ),
                    )

                # Log the action
                self.log_change(
                    request,
                    program,
                    f"Bulk invited {created_count} participants by {request.user.username}",
                )

                return redirect("admin:programs_program_change", program.id)
        else:
            form = BulkInviteForm()

        # Get invitation stats for context
        invitation_stats = {
            "total": ProgramInvitation.objects.filter(program=program).count(),
            "pending": ProgramInvitation.objects.filter(
                program=program, status=ProgramInvitation.Status.PENDING
            ).count(),
            "accepted": ProgramInvitation.objects.filter(
                program=program, status=ProgramInvitation.Status.ACCEPTED
            ).count(),
        }

        context = {
            **self.admin_site.each_context(request),
            "program": program,
            "form": form,
            "invitation_stats": invitation_stats,
            "title": f"Bulk Invite - {program.title}",
        }

        return render(request, "admin/programs/bulk_invite.html", context)

    def _send_invitation_email(self, request, invitation):
        """Send an invitation email."""
        from django.core.mail import send_mail
        from django.conf import settings

        invite_url = request.build_absolute_uri(
            reverse("enrollments:invitation_respond", args=[invitation.token])
        )

        subject = f"You're invited to {invitation.program.title}"

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

    # ========== BULK ACTIONS ==========

    @admin.action(description="Export selected programs to CSV")
    def export_programs_csv(self, request, queryset):
        """Bulk export programs"""
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="programs_{datetime.now().strftime("%Y%m%d")}.csv"'
        )

        writer = csv.writer(response)
        writer.writerow(
            ["Code", "Title", "Type", "Start Date", "End Date", "Enrollments"]
        )

        for program in queryset.order_by("code"):
            writer.writerow(
                [
                    program.code,
                    program.title,
                    program.type,
                    (
                        program.start_date.strftime("%Y-%m-%d")
                        if program.start_date
                        else ""
                    ),
                    program.end_date.strftime("%Y-%m-%d") if program.end_date else "",
                    program.enrollments.count(),
                ]
            )

        self.message_user(request, f"Exported {queryset.count()} programs")
        return response

    @admin.action(
        description="🏷️ Export name badges (First, Last) for selected programs"
    )
    def export_bulk_name_badges(self, request, queryset):
        """
        Export name badges CSV for multiple programs at once.
        Only includes accepted participants who haven't withdrawn.
        """
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="name_badges_{datetime.now().strftime("%Y%m%d")}.csv"'
        )

        writer = csv.writer(response)
        writer.writerow(["First Name", "Last Name", "Program"])

        total_count = 0
        for program in queryset.order_by("start_date"):
            # Only accepted, not withdrawn
            attendees = (
                Enrollment.objects.filter(
                    workshop=program,
                    accepted_at__isnull=False,
                    declined_at__isnull=True,
                )
                .select_related("person")
                .order_by("person__last_name", "person__first_name")
            )

            for enrollment in attendees:
                person = enrollment.person
                if person:
                    writer.writerow(
                        [
                            person.first_name or "",
                            person.last_name or "",
                        ]
                    )
                    total_count += 1

        self.message_user(
            request,
            f"Exported {total_count} name badges from {queryset.count()} program(s)",
        )
        return response

    # ========== SINGLE PROGRAM VIEWS ==========

    def export_name_badges(self, request, program_id):
        """
        Export name badges CSV for a single program.
        Only includes accepted participants who haven't withdrawn.
        Format: First Name, Last Name (for Avery label import)
        """
        program = get_object_or_404(Program, id=program_id)

        if not self.has_view_permission(request, program):
            return HttpResponse("Permission denied", status=403)

        # Only accepted, not withdrawn
        attendees = (
            Enrollment.objects.filter(
                workshop=program,
                accepted_at__isnull=False,
                declined_at__isnull=True,
            )
            .select_related("person")
            .order_by("person__last_name", "person__first_name")
        )

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="badges_{program.code}_{datetime.now().strftime("%Y%m%d")}.csv"'
        )

        writer = csv.writer(response)
        writer.writerow(["First Name", "Last Name"])

        for enrollment in attendees:
            person = enrollment.person
            if person:
                writer.writerow(
                    [
                        person.first_name or "",
                        person.last_name or "",
                    ]
                )

        self.log_change(request, program, f"Exported {attendees.count()} name badges")

        return response


# =============================================================================
# PROXY MODEL ADMINS
# These appear as separate entries in the admin sidebar
# =============================================================================


class UpcomingProgramFilter(admin.SimpleListFilter):
    """Filter for upcoming vs past programs."""

    title = "Status"
    parameter_name = "status"

    def lookups(self, request, model_admin):
        return [
            ("upcoming", "Upcoming"),
            ("past", "Past"),
            ("accepting", "Accepting Applications"),
        ]

    def queryset(self, request, queryset):
        today = timezone.localdate()
        if self.value() == "upcoming":
            return queryset.filter(end_date__gte=today)
        if self.value() == "past":
            return queryset.filter(end_date__lt=today)
        if self.value() == "accepting":
            return queryset.filter(
                application_mode=Program.ApplicationMode.OPEN,
                application_deadline__gte=timezone.now(),
            )
        return queryset


@admin.register(Workshop)
class WorkshopAdmin(ProgramAdmin):
    """Admin for Workshops only - filtered view."""

    list_display = (
        "code",
        "short_title",
        "dates_display",
        "application_mode",
        "enrollment_count",
        "staff_actions",
    )

    # Simpler filters - no type filter needed
    list_filter = (UpcomingProgramFilter, "application_mode", "online")

    def get_queryset(self, request):
        """Already filtered by proxy model manager."""
        return super().get_queryset(request)

    def save_model(self, request, obj, form, change):
        """Ensure type is set to WORKSHOP for new objects."""
        if not change:
            obj.type = Program.ProgramType.WORKSHOP
        super().save_model(request, obj, form, change)


@admin.register(SQuaRE)
class SQuaREAdmin(ProgramAdmin):
    """Admin for SQuaREs only - filtered view."""

    list_display = (
        "code",
        "title",
        "start_date",
        "end_date",
        "application_deadline",
        "enrollment_count",
        "staff_actions",
    )

    list_filter = (UpcomingProgramFilter, "application_mode", "online")

    def save_model(self, request, obj, form, change):
        """Ensure type is set to SQUARE for new objects."""
        if not change:
            obj.type = Program.ProgramType.SQUARE
        super().save_model(request, obj, form, change)


@admin.register(ResearchCommunity)
class ResearchCommunityAdmin(ProgramAdmin):
    """Admin for Research Communities only."""

    list_display = (
        "code",
        "title",
        "start_date",
        "end_date",
        "enrollment_count",
        "staff_actions",
    )

    list_filter = (UpcomingProgramFilter, "online")

    def save_model(self, request, obj, form, change):
        """Ensure type is set to COMMUNITY for new objects."""
        if not change:
            obj.type = Program.ProgramType.COMMUNITY
        super().save_model(request, obj, form, change)
