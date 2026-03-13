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
        "checklist_link",
        "quick_actions",
    )
    frontend_editable_fields = ("title",)
    readonly_fields = ("code",)  # Auto-generated, not editable

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

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("checklist")

    # Bulk actions
    actions = ["export_programs_csv", "export_bulk_name_badges"]

    # Enable autocomplete for parent_square with search
    autocomplete_fields = ["parent_square"]

    def get_search_results(self, request, queryset, search_term):
        """
        Filter autocomplete results for parent_square to only show SQuaREs.
        Allows searching by code number or title.
        """
        queryset, use_distinct = super().get_search_results(
            request, queryset, search_term
        )

        # Check if this is an autocomplete request for parent_square
        if request.GET.get("field_name") == "parent_square":
            try:
                queryset = queryset.filter(
                    type__in=[Program.ProgramType.SQUARE, Program.ProgramType.VSQUARE],
                    parent_square__isnull=True,  # Only root meetings can be parents
                )
            except Exception:
                # Field may not exist if migrations haven't run
                pass

        return queryset, use_distinct

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Limit parent_square choices to only SQuaRE root programs."""
        if db_field.name == "parent_square":
            try:
                kwargs["queryset"] = Program.objects.filter(
                    type__in=[Program.ProgramType.SQUARE, Program.ProgramType.VSQUARE],
                    parent_square__isnull=True,
                ).order_by("-start_date", "title")
            except Exception:
                # Field may not exist if migrations haven't run
                pass
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

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
            path(
                "<int:program_id>/manage-enrollments/",
                self.admin_site.admin_view(self.manage_enrollments_view),
                name="programs_program_manage_enrollments",
            ),
            path(
                "<int:program_id>/import-enrollments/",
                self.admin_site.admin_view(self.import_enrollments_view),
                name="programs_program_import_enrollments",
            ),
            path(
                "<int:program_id>/send-enrollment-invites/",
                self.admin_site.admin_view(self.send_enrollment_invites_view),
                name="programs_program_send_enrollment_invites",
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

    def checklist_link(self, obj):
        """Link to the program's checklist page."""
        url = reverse("checklists:program_checklist", args=[obj.code])
        checklist = getattr(obj, "checklist", None)
        if checklist:
            summary = checklist.completion_summary()
            return format_html(
                '<a href="{}" style="white-space:nowrap;">✅ Checklist ({}/{})</a>',
                url, summary["done"], summary["total"],
            )
        return format_html('<a href="{}" style="white-space:nowrap;">📋 Checklist</a>', url)

    checklist_link.short_description = "Checklist"

    def quick_actions(self, obj):
        """Action links displayed vertically"""
        applicants_url = reverse("admin:programs_program_applicants", args=[obj.id])
        export_url = reverse("admin:programs_program_export_csv", args=[obj.id])
        emails_url = reverse("admin:programs_program_emails", args=[obj.id])
        invite_url = reverse("admin:programs_program_bulk_invite", args=[obj.id])
        badges_url = reverse("admin:programs_program_name_badges", args=[obj.id])
        manage_url = reverse("admin:programs_program_manage_enrollments", args=[obj.id])

        return format_html(
            '<a href="{}">👥 Applicants</a><br>'
            '<a href="{}">📥 CSV</a><br>'
            '<a href="{}">📧 Emails</a><br>'
            '<a href="{}">✉️ Invite</a><br>'
            '<a href="{}">🏷️ Badges</a><br>'
            '<a href="{}">⚙️ Manage</a>',
            applicants_url,
            export_url,
            emails_url,
            invite_url,
            badges_url,
            manage_url,
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

            # Use person fields if linked, otherwise use enrollment snapshot fields
            if person:
                last_name = person.last_name or ""
                first_name = person.first_name or ""
                email = person.email_address or ""
                orcid = person.orcid_id or ""
                institution = person.institution or ""
            else:
                last_name = enrollment.last_name or ""
                first_name = enrollment.first_name or ""
                email = enrollment.email_snap or ""
                orcid = enrollment.orcid_snap or ""
                institution = enrollment.institution or ""

            writer.writerow(
                [
                    last_name,
                    first_name,
                    email,
                    orcid,
                    institution,
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

    def manage_enrollments_view(self, request, program_id):
        """
        Unified enrollment management page:
        - Import enrollments from CSV
        - View pending invites
        - Send invite emails
        """
        program = get_object_or_404(Program, id=program_id)

        if not self.has_change_permission(request, program):
            return HttpResponse("Permission denied", status=403)

        # Get enrollment stats
        pending_invites = Enrollment.objects.filter(
            workshop=program,
            person__isnull=True,
            invite_sent_at__isnull=True,
        ).order_by("created_at")

        invited_awaiting = Enrollment.objects.filter(
            workshop=program,
            person__isnull=True,
            invite_sent_at__isnull=False,
        ).order_by("-invite_sent_at")

        confirmed = (
            Enrollment.objects.filter(
                workshop=program,
                person__isnull=False,
            )
            .select_related("person")
            .order_by("-created_at")
        )

        context = {
            **self.admin_site.each_context(request),
            "program": program,
            "pending_invites": pending_invites,
            "invited_awaiting": invited_awaiting,
            "confirmed": confirmed,
            "opts": self.model._meta,
            "title": f"Manage Enrollments: {program.title}",
        }

        return render(request, "admin/programs/manage_enrollments.html", context)

    def import_enrollments_view(self, request, program_id):
        """Import enrollments from CSV data."""
        import csv
        import io

        program = get_object_or_404(Program, id=program_id)

        if not self.has_change_permission(request, program):
            return HttpResponse("Permission denied", status=403)

        if request.method != "POST":
            return redirect(
                "admin:programs_program_manage_enrollments", program_id=program_id
            )

        csv_data = request.POST.get("csv_data", "").strip()
        if not csv_data:
            messages.error(request, "No CSV data provided.")
            return redirect(
                "admin:programs_program_manage_enrollments", program_id=program_id
            )

        # Parse CSV
        reader = csv.DictReader(io.StringIO(csv_data))

        created = 0
        skipped = 0
        errors = []

        # Get existing emails for this program to check duplicates
        existing_emails = set(
            Enrollment.objects.filter(workshop=program)
            .exclude(email_snap__isnull=True)
            .exclude(email_snap="")
            .values_list("email_snap", flat=True)
        )

        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
            try:
                # Normalize field names (handle various CSV formats)
                first_name = (
                    row.get("first_name")
                    or row.get("First Name")
                    or row.get("firstname")
                    or ""
                )
                last_name = (
                    row.get("last_name")
                    or row.get("Last Name")
                    or row.get("lastname")
                    or ""
                )
                email = (
                    row.get("email")
                    or row.get("Email")
                    or row.get("email_address")
                    or ""
                )
                funding = row.get("funding") or row.get("Funding") or ""

                email = email.strip().lower()

                if not email:
                    errors.append(f"Row {row_num}: Missing email address")
                    continue

                # Skip duplicates
                if email in existing_emails:
                    skipped += 1
                    continue

                # Create enrollment
                Enrollment.objects.create(
                    workshop=program,
                    first_name=first_name.strip(),
                    last_name=last_name.strip(),
                    email_snap=email,
                    funding=funding.strip(),
                    source=Enrollment.Source.STAFF,
                    person=None,
                    invite_sent_at=None,
                )
                existing_emails.add(email)
                created += 1

            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")

        # Show results
        if created:
            messages.success(request, f"Created {created} new enrollment(s).")
        if skipped:
            messages.info(request, f"Skipped {skipped} duplicate(s).")
        if errors:
            messages.warning(
                request, f"{len(errors)} error(s): {'; '.join(errors[:5])}"
            )

        return redirect(
            "admin:programs_program_manage_enrollments", program_id=program_id
        )

    def send_enrollment_invites_view(self, request, program_id):
        """Send invitation emails for selected enrollments."""
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        from django.conf import settings

        program = get_object_or_404(Program, id=program_id)

        if not self.has_change_permission(request, program):
            return HttpResponse("Permission denied", status=403)

        if request.method != "POST":
            return redirect(
                "admin:programs_program_manage_enrollments", program_id=program_id
            )

        # Get selected enrollment IDs
        enrollment_ids = request.POST.getlist("enrollment_ids")

        if not enrollment_ids:
            messages.warning(request, "No enrollments selected.")
            return redirect(
                "admin:programs_program_manage_enrollments", program_id=program_id
            )

        enrollments = Enrollment.objects.filter(
            id__in=enrollment_ids,
            workshop=program,
            person__isnull=True,
            invite_sent_at__isnull=True,
        )

        sent_count = 0
        error_count = 0

        for enrollment in enrollments:
            try:
                # Generate token for this enrollment
                enrollment.generate_invite_token()
                enrollment.save(update_fields=["invite_token"])

                # Build invite URL using enrollment token
                invite_url = request.build_absolute_uri(
                    reverse(
                        "enrollments:enrollment_respond", args=[enrollment.invite_token]
                    )
                )

                # Send email
                subject = f"Invitation: {program.title}"
                context = {
                    "first_name": enrollment.first_name or "Participant",
                    "program": program,
                    "invite_url": invite_url,
                    "accept_url": f"{invite_url}?action=accept",
                    "decline_url": f"{invite_url}?action=decline",
                }

                html_message = render_to_string(
                    "emails/program_invitation.html", context
                )
                plain_message = render_to_string(
                    "emails/program_invitation.txt", context
                )

                send_mail(
                    subject=subject,
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[enrollment.email_snap],
                    html_message=html_message,
                    fail_silently=False,
                )

                # Mark as sent using the send_invite method
                enrollment.send_invite(sent_by=request.user)

                sent_count += 1

            except Exception as e:
                error_count += 1
                messages.error(
                    request, f"Failed to send to {enrollment.email_snap}: {e}"
                )

        if sent_count:
            messages.success(request, f"Sent {sent_count} invitation(s).")
        if error_count:
            messages.warning(request, f"{error_count} email(s) failed to send.")

        return redirect(
            "admin:programs_program_manage_enrollments", program_id=program_id
        )


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
        "checklist_link",
        "staff_actions",
    )

    # Simpler filters - no type filter needed
    list_filter = (UpcomingProgramFilter, "application_mode", "online")

    def save_model(self, request, obj, form, change):
        """Ensure type is set to WORKSHOP for new objects."""
        if not change:
            obj.type = Program.ProgramType.WORKSHOP
        super().save_model(request, obj, form, change)


class MeetingNumberFilter(admin.SimpleListFilter):
    """Filter SQuaREs by meeting number."""

    title = "Meeting"
    parameter_name = "meeting"

    def lookups(self, request, model_admin):
        return [
            ("1", "1st Meeting"),
            ("2", "2nd Meeting"),
            ("3", "3rd Meeting"),
            ("4", "4th Meeting"),
            ("5", "5th Meeting"),
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(meeting_number=int(self.value()))
        return queryset


@admin.register(SQuaRE)
class SQuaREAdmin(ProgramAdmin):
    """Admin for SQuaREs only - filtered view with meeting linking support."""

    list_display = (
        "code",
        "short_title",
        "meeting_badge",
        "parent_link",
        "dates_display",
        "enrollment_count",
        "checklist_link",
        "square_actions",
    )

    list_filter = (
        UpcomingProgramFilter,
        MeetingNumberFilter,
        "application_mode",
        "online",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "title",
                    "abbreviation",
                    "type",
                    "meeting_number",
                    "parent_square",
                )
            },
        ),
        (
            "Dates",
            {
                "fields": (
                    "start_date",
                    "end_date",
                    "application_deadline",
                    "application_mode",
                )
            },
        ),
        ("Location", {"fields": ("location", "online")}),
        (
            "Organizers",
            {
                "fields": (
                    ("organizer1", "organizeremail1"),
                    ("organizer2", "organizeremail2"),
                    ("organizer3", "organizeremail3"),
                    ("scribe", "scribe_email"),
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Description",
            {
                "fields": ("description",),
                "classes": ("collapse",),
            },
        ),
    )

    def get_urls(self):
        """Add custom URLs for SQuaRE-specific actions."""
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:program_id>/create-next-meeting/",
                self.admin_site.admin_view(self.create_next_meeting_view),
                name="programs_square_create_next_meeting",
            ),
        ]
        return custom_urls + urls

    def meeting_badge(self, obj):
        """Display meeting number as colored badge."""
        meeting_num = getattr(obj, "meeting_number", None)
        if not meeting_num:
            return "—"
        colors = {
            1: "#0d6efd",
            2: "#198754",
            3: "#dc3545",
            4: "#6f42c1",
            5: "#fd7e14",
        }
        color = colors.get(meeting_num, "#6c757d")
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">Meeting {}</span>',
            color,
            meeting_num,
        )

    meeting_badge.short_description = "Meeting"
    meeting_badge.admin_order_field = "meeting_number"

    def parent_link(self, obj):
        """Show link to parent SQuaRE (meeting 1) if applicable."""
        try:
            parent = getattr(obj, "parent_square", None)
            if parent:
                url = reverse("admin:programs_square_change", args=[parent.id])
                return format_html(
                    '<a href="{}" title="{}">← Meeting 1</a>', url, parent.title
                )

            meeting_num = getattr(obj, "meeting_number", None)
            if meeting_num == 1 or meeting_num is None:
                subsequent = getattr(obj, "subsequent_meetings", None)
                if subsequent:
                    count = subsequent.count()
                    if count > 0:
                        return format_html(
                            '<span style="color: #198754;">Root ({} linked)</span>',
                            count,
                        )
                return "Root"
        except Exception:
            return "—"
        return "—"

    parent_link.short_description = "Group"

    def square_actions(self, obj):
        """Action links for SQuaREs including Create Next Meeting."""
        from django.urls import NoReverseMatch

        try:
            applicants_url = reverse("admin:programs_program_applicants", args=[obj.id])
            export_url = reverse("admin:programs_program_export_csv", args=[obj.id])
            manage_url = reverse(
                "admin:programs_program_manage_enrollments", args=[obj.id]
            )

            meeting_num = getattr(obj, "meeting_number", None)
            if meeting_num is None or meeting_num < 5:
                create_url = reverse(
                    "admin:programs_square_create_next_meeting", args=[obj.id]
                )
                return format_html(
                    '<a href="{}">👥</a> <a href="{}">📥</a> <a href="{}">⚙️</a> '
                    '<a href="{}" style="background:#198754;color:white;padding:2px 6px;'
                    'border-radius:3px;text-decoration:none;" '
                    'title="Create next meeting with same participants">➕ Next</a>',
                    applicants_url,
                    export_url,
                    manage_url,
                    create_url,
                )

            return format_html(
                '<a href="{}">👥</a> <a href="{}">📥</a> <a href="{}">⚙️</a>',
                applicants_url,
                export_url,
                manage_url,
            )
        except NoReverseMatch:
            return "—"

    square_actions.short_description = "Actions"

    def create_next_meeting_view(self, request, program_id):
        """Create the next meeting of a SQuaRE, copying participants."""
        source = get_object_or_404(
            Program, id=program_id, type=Program.ProgramType.SQUARE
        )

        root = source.square_root
        current_max = root.all_square_meetings.order_by("-meeting_number").first()
        current_meeting_num = (
            current_max.meeting_number
            if current_max and current_max.meeting_number
            else 1
        )
        next_meeting_num = current_meeting_num + 1

        if next_meeting_num > 5:
            messages.error(request, "Maximum of 5 meetings reached for this SQuaRE.")
            return redirect(reverse("admin:programs_square_change", args=[program_id]))

        if request.method == "POST":
            new_meeting = Program.objects.create(
                title=root.title,
                abbreviation=root.abbreviation,
                type=Program.ProgramType.SQUARE,
                meeting_number=next_meeting_num,
                parent_square=root,
                location=source.location,
                online=source.online,
                organizer1=source.organizer1,
                organizeremail1=source.organizeremail1,
                organizer2=source.organizer2,
                organizeremail2=source.organizeremail2,
                organizer3=source.organizer3,
                organizeremail3=source.organizeremail3,
                scribe=source.scribe,
                scribe_email=source.scribe_email,
                description=source.description,
                application_mode=Program.ApplicationMode.INVITE_ONLY,
            )

            copied_count = 0
            source_enrollments = Enrollment.objects.filter(
                workshop=source,
                accepted_at__isnull=False,
                declined_at__isnull=True,
            ).select_related("person")

            for enrollment in source_enrollments:
                Enrollment.objects.create(
                    workshop=new_meeting,
                    person=enrollment.person,
                    source=Enrollment.Source.STAFF,
                    first_name=enrollment.first_name,
                    middle_name=enrollment.middle_name,
                    last_name=enrollment.last_name,
                    email_snap=enrollment.email_snap,
                    orcid_snap=enrollment.orcid_snap,
                    institution=enrollment.institution,
                    accepted_at=timezone.now(),
                )
                copied_count += 1

            messages.success(
                request,
                f"Created Meeting {next_meeting_num} for '{root.title}' "
                f"with {copied_count} participant(s) copied.",
            )

            return redirect(
                reverse("admin:programs_square_change", args=[new_meeting.id])
            )

        all_participants = root.get_all_square_participants()
        source_participants = Enrollment.objects.filter(
            workshop=source,
            accepted_at__isnull=False,
            declined_at__isnull=True,
        ).select_related("person")

        context = {
            **self.admin_site.each_context(request),
            "source": source,
            "root": root,
            "next_meeting_num": next_meeting_num,
            "all_meetings": root.all_square_meetings,
            "source_participants": source_participants,
            "all_participants": all_participants,
            "title": f"Create Meeting {next_meeting_num} - {root.title}",
        }

        return render(request, "admin/programs/create_next_meeting.html", context)

    def save_model(self, request, obj, form, change):
        """Ensure type is set to SQUARE for new objects."""
        if not change:
            obj.type = Program.ProgramType.SQUARE
            if not obj.meeting_number and not obj.parent_square:
                obj.meeting_number = 1
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
