from datetime import datetime, time, timedelta

from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from .models import (
    Activity,
    AIMHoliday,
    DirectorDefaultAllocation,
    PDFSnapshot,
    PeriodReport,
    PeriodReportLine,
    ReportingCalendar,
    ReportingPeriod,
    ReportingWeek,
    SalaryIndirectAllocation,
    StaffTimesheetProfile,
    WeeklyTimesheet,
    WeeklyTimesheetLine,
)


# =============================================================================
# ACTIVITY
# =============================================================================


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "default_grant_code",
        "classification",
        "valid_from",
        "valid_to",
        "is_preset",
        "is_grant_addon",
        "is_holiday_activity",
        "is_active",
        "sort_order",
    ]
    list_editable = ["valid_from", "valid_to", "sort_order", "is_active", "is_preset", "is_holiday_activity"]
    list_filter = ["classification", "is_preset", "is_holiday_activity", "is_active"]
    ordering = ["sort_order", "name"]


# =============================================================================
# STAFF PROFILE
# =============================================================================


@admin.register(StaffTimesheetProfile)
class StaffTimesheetProfileAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "staff_type",
        "supervisor",
        "title",
        "hire_date",
        "is_active",
    ]
    list_filter = ["staff_type", "is_active"]
    search_fields = ["user__first_name", "user__last_name", "user__email"]
    raw_id_fields = ["user", "supervisor"]


# =============================================================================
# REPORTING CALENDAR
# =============================================================================


@admin.register(ReportingCalendar)
class ReportingCalendarAdmin(admin.ModelAdmin):
    list_display = ["anchor_start_date", "created_at", "period_count"]
    readonly_fields = ["created_at"]
    actions = ["generate_periods_action"]

    def period_count(self, obj):
        return obj.periods.count()

    period_count.short_description = "Periods Generated"

    @admin.action(
        description="Generate reporting periods (24 months back, 13 months forward)"
    )
    def generate_periods_action(self, request, queryset):
        total_created = 0
        for calendar in queryset:
            created, skipped = calendar.generate_periods(
                months_back=24, months_forward=13
            )
            total_created += created
        self.message_user(
            request,
            f"Created {total_created} new period(s) across {queryset.count()} calendar(s).",
        )


# =============================================================================
# REPORTING PERIODS
# =============================================================================


class ReportingWeekInline(admin.TabularInline):
    model = ReportingWeek
    extra = 0
    fields = ["week_number", "start_date", "end_date", "due_date"]
    ordering = ["week_number"]


@admin.register(ReportingPeriod)
class ReportingPeriodAdmin(admin.ModelAdmin):
    list_display = [
        "label",
        "period_index",
        "start_date",
        "end_date",
        "submission_deadline",
        "is_locked",
        "week_count",
    ]
    list_filter = ["is_locked", "calendar"]
    search_fields = ["label"]
    inlines = [ReportingWeekInline]
    actions = ["lock_periods", "unlock_periods"]
    readonly_fields = ["period_index"]

    def save_model(self, request, obj, form, change):
        if not obj.submission_deadline:
            deadline_naive = datetime.combine(
                obj.end_date + timedelta(days=3), time(14, 0)
            )
            obj.submission_deadline = timezone.make_aware(deadline_naive)
        super().save_model(request, obj, form, change)
        if not obj.weeks.exists():
            current = obj.start_date
            week_num = 1
            while current <= obj.end_date:
                week_end = min(current + timedelta(days=6), obj.end_date)
                ReportingWeek.objects.create(
                    period=obj,
                    week_number=week_num,
                    start_date=current,
                    end_date=week_end,
                )
                current += timedelta(days=7)
                week_num += 1
            self.message_user(
                request,
                f"Auto-generated {obj.weeks.count()} week(s) for '{obj.label}'.",
            )

    def week_count(self, obj):
        return obj.weeks.count()

    week_count.short_description = "Weeks"

    @admin.action(description="Lock selected periods (prevent edits)")
    def lock_periods(self, request, queryset):
        updated = queryset.update(is_locked=True)
        self.message_user(request, f"{updated} period(s) locked.")

    @admin.action(description="Unlock selected periods")
    def unlock_periods(self, request, queryset):
        updated = queryset.update(is_locked=False)
        self.message_user(request, f"{updated} period(s) unlocked.")


# =============================================================================
# WEEKLY TIMESHEETS
# =============================================================================


class WeeklyTimesheetLineInline(admin.TabularInline):
    model = WeeklyTimesheetLine
    extra = 0
    fields = [
        "activity",
        "custom_activity_name",
        "grant_code",
        "hours_sun",
        "hours_mon",
        "hours_tue",
        "hours_wed",
        "hours_thu",
        "hours_fri",
        "hours_sat",
        "description",
    ]


@admin.register(WeeklyTimesheet)
class WeeklyTimesheetAdmin(admin.ModelAdmin):
    list_display = [
        "staff",
        "week",
        "status",
        "total_hours_display",
        "submitted_at",
        "supervisor_approved_at",
    ]
    list_filter = ["status"]
    search_fields = ["staff__user__first_name", "staff__user__last_name"]
    readonly_fields = [
        "submitted_at",
        "supervisor_approved_at",
        "supervisor_approved_by",
        "created_at",
        "updated_at",
    ]
    inlines = [WeeklyTimesheetLineInline]
    actions = ["unlock_to_draft", "supervisor_approve_timesheets"]

    def total_hours_display(self, obj):
        return obj.total_hours

    total_hours_display.short_description = "Total Hours"

    @admin.action(
        description="Unlock selected timesheets back to Draft (use with care)"
    )
    def unlock_to_draft(self, request, queryset):
        updated = queryset.update(
            status=WeeklyTimesheet.Status.DRAFT,
            submitted_at=None,
        )
        self.message_user(request, f"{updated} timesheet(s) reverted to Draft.")

    @admin.action(description="Supervisor-approve selected submitted timesheets")
    def supervisor_approve_timesheets(self, request, queryset):
        submitted = queryset.filter(status=WeeklyTimesheet.Status.SUBMITTED)
        now = timezone.now()
        updated = submitted.update(
            supervisor_approved_at=now,
            supervisor_approved_by=request.user,
        )
        skipped = queryset.count() - updated
        msg = f"Approved {updated} timesheet(s)."
        if skipped:
            msg += f" {skipped} skipped (not in Submitted status)."
        self.message_user(request, msg)


# =============================================================================
# PERIOD REPORTS
# =============================================================================


STATUS_COLOURS = {
    PeriodReport.Status.DRAFT: "#6c757d",
    PeriodReport.Status.SUBMITTED: "#0d6efd",
    PeriodReport.Status.SUPERVISOR_APPROVED: "#198754",
    PeriodReport.Status.PROCESSED: "#6f42c1",
}


class PeriodReportLineInline(admin.TabularInline):
    model = PeriodReportLine
    extra = 0
    fields = [
        "activity_name_snapshot",
        "grant_code_snapshot",
        "classification_snapshot",
        "total_hours",
        "percentage",
        "duties_description",
    ]
    readonly_fields = [
        "activity_name_snapshot",
        "grant_code_snapshot",
        "classification_snapshot",
        "total_hours",
        "percentage",
    ]


@admin.register(PeriodReport)
class PeriodReportAdmin(admin.ModelAdmin):
    list_display = [
        "staff",
        "period",
        "submission_type",
        "status_badge",
        "supervisor_approved_at",
        "processed_at",
    ]
    list_filter = ["status", "submission_type"]
    search_fields = ["staff__user__first_name", "staff__user__last_name"]
    readonly_fields = [
        "status",
        "submission_type",
        "supervisor_approved_at",
        "supervisor_approved_by",
        "processed_at",
        "processed_by",
        "generated_at",
        "created_at",
        "updated_at",
        "supervisor_name_snapshot",
        "employee_title_snapshot",
        "employee_name_snapshot",
    ]
    inlines = [PeriodReportLineInline]
    actions = [
        "action_supervisor_approve",
        "action_mark_processed",
        "action_unlock_to_draft",
    ]

    def status_badge(self, obj):
        colour = STATUS_COLOURS.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:0.8em">{}</span>',
            colour,
            obj.get_status_display(),
        )

    status_badge.short_description = "Status"

    @admin.action(description="Supervisor-approve selected submitted reports")
    def action_supervisor_approve(self, request, queryset):
        eligible = queryset.filter(status=PeriodReport.Status.SUBMITTED)
        count = 0
        for report in eligible:
            report.supervisor_approve(approved_by=request.user)
            count += 1
        skipped = queryset.count() - count
        msg = f"Supervisor-approved {count} report(s)."
        if skipped:
            msg += f" {skipped} skipped (must be in Submitted status)."
        self.message_user(request, msg)

    @admin.action(description="Mark selected supervisor-approved reports as Processed")
    def action_mark_processed(self, request, queryset):
        eligible = queryset.filter(status=PeriodReport.Status.SUPERVISOR_APPROVED)
        count = 0
        for report in eligible:
            report.mark_processed(processed_by=request.user)
            count += 1
        skipped = queryset.count() - count
        msg = f"Marked {count} report(s) as Processed."
        if skipped:
            msg += f" {skipped} skipped (must be in Supervisor Approved status)."
        self.message_user(request, msg)

    @admin.action(description="Unlock selected reports back to Draft (admin override)")
    def action_unlock_to_draft(self, request, queryset):
        updated = queryset.update(
            status=PeriodReport.Status.DRAFT,
            supervisor_approved_at=None,
            supervisor_approved_by=None,
            processed_at=None,
            processed_by=None,
        )
        self.message_user(request, f"{updated} report(s) reverted to Draft.")


# =============================================================================
# PDF SNAPSHOTS
# =============================================================================


@admin.register(PDFSnapshot)
class PDFSnapshotAdmin(admin.ModelAdmin):
    list_display = [
        "__str__",
        "pdf_type",
        "version",
        "generated_by",
        "generated_at",
        "file_link",
    ]
    list_filter = ["pdf_type"]
    readonly_fields = ["checksum", "generated_at", "version"]

    def file_link(self, obj):
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank">Download</a>', obj.file.url
            )
        return "—"

    file_link.short_description = "File"


# =============================================================================
# HOLIDAYS & DIRECTOR DEFAULTS
# =============================================================================


@admin.register(AIMHoliday)
class AIMHolidayAdmin(admin.ModelAdmin):
    list_display = ["name", "date"]
    ordering = ["date"]


@admin.register(DirectorDefaultAllocation)
class DirectorDefaultAllocationAdmin(admin.ModelAdmin):
    list_display = ["profile", "main_grant_code", "main_grant_pct"]
    search_fields = ["profile__user__first_name", "profile__user__last_name"]
    raw_id_fields = ["profile"]


@admin.register(SalaryIndirectAllocation)
class SalaryIndirectAllocationAdmin(admin.ModelAdmin):
    list_display = [
        "profile",
        "hours_administrative",
        "hours_other_activity",
        "hours_sick_personal",
        "hours_vacation",
        "hours_fundraising_pr",
        "hours_other_unallowable",
    ]
    search_fields = ["profile__user__first_name", "profile__user__last_name"]
    raw_id_fields = ["profile"]
