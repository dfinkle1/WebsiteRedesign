from datetime import timedelta

from django import forms
from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Activity,
    AIMHoliday,
    DirectorDefaultAllocation,
    DirectorPeriodSubmission,
    DirectorSubmissionLine,
    PDFSnapshot,
    PeriodReport,
    PeriodReportLine,
    ReportingPeriod,
    ReportingWeek,
    StaffTimesheetProfile,
    WeeklyTimesheet,
    WeeklyTimesheetLine,
)
from .services import initialize_period_report


# =============================================================================
# ACTIVITY
# =============================================================================


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ["name", "default_grant_code", "classification", "is_preset", "is_grant_addon", "is_active", "sort_order"]
    list_editable = ["sort_order", "is_active", "is_preset"]
    list_filter = ["classification", "is_preset", "is_active"]
    ordering = ["sort_order", "name"]


# =============================================================================
# STAFF PROFILE
# =============================================================================


@admin.register(StaffTimesheetProfile)
class StaffTimesheetProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "staff_type", "supervisor", "title", "hire_date", "is_active"]
    list_filter = ["staff_type", "is_active"]
    search_fields = ["user__first_name", "user__last_name", "user__email"]
    raw_id_fields = ["user", "supervisor"]


# =============================================================================
# REPORTING CALENDAR
# =============================================================================


class ReportingPeriodForm(forms.ModelForm):
    class Meta:
        model = ReportingPeriod
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_date")
        end = cleaned.get("end_date")
        staff_type = cleaned.get("staff_type")
        if start and end and staff_type:
            delta = (end - start).days + 1
            expected = 28 if staff_type == ReportingPeriod.StaffType.SALARY else 14
            week_count = 4 if staff_type == ReportingPeriod.StaffType.SALARY else 2
            if delta != expected:
                raise forms.ValidationError(
                    f"{staff_type.title()} periods must span exactly {expected} days ({week_count} weeks). "
                    f"Selected range is {delta} day(s). Adjust the end date to {start + timedelta(days=expected - 1)}."
                )
        return cleaned


class ReportingWeekInline(admin.TabularInline):
    model = ReportingWeek
    extra = 0
    fields = ["week_number", "start_date", "end_date", "due_date"]
    ordering = ["week_number"]


@admin.register(ReportingPeriod)
class ReportingPeriodAdmin(admin.ModelAdmin):
    form = ReportingPeriodForm
    list_display = ["label", "staff_type", "period_type", "start_date", "end_date", "submission_deadline", "is_locked", "week_count"]
    list_filter = ["staff_type", "period_type", "is_locked"]
    inlines = [ReportingWeekInline]
    actions = ["lock_periods", "unlock_periods"]

    def save_model(self, request, obj, form, change):
        if not obj.submission_deadline:
            from datetime import datetime, time
            from django.utils import timezone
            deadline_naive = datetime.combine(obj.end_date + timedelta(days=3), time(14, 0))
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

    @admin.action(description="Lock selected periods")
    def lock_periods(self, request, queryset):
        queryset.update(is_locked=True)

    @admin.action(description="Unlock selected periods")
    def unlock_periods(self, request, queryset):
        queryset.update(is_locked=False)


# =============================================================================
# WEEKLY TIMESHEETS
# =============================================================================


class WeeklyTimesheetLineInline(admin.TabularInline):
    model = WeeklyTimesheetLine
    extra = 0
    fields = ["activity", "grant_code", "hours_sun", "hours_mon", "hours_tue", "hours_wed", "hours_thu", "hours_fri", "hours_sat", "description"]
    readonly_fields = []


@admin.register(WeeklyTimesheet)
class WeeklyTimesheetAdmin(admin.ModelAdmin):
    list_display = ["staff", "week", "status", "total_hours_display", "submitted_at"]
    list_filter = ["status", "week__period__staff_type"]
    search_fields = ["staff__user__first_name", "staff__user__last_name"]
    readonly_fields = ["submitted_at", "created_at", "updated_at"]
    inlines = [WeeklyTimesheetLineInline]
    actions = ["unlock_to_draft"]

    def total_hours_display(self, obj):
        return obj.total_hours
    total_hours_display.short_description = "Total Hours"

    @admin.action(description="Unlock selected timesheets back to Draft (use with care)")
    def unlock_to_draft(self, request, queryset):
        updated = queryset.update(status=WeeklyTimesheet.Status.DRAFT, submitted_at=None)
        self.message_user(request, f"{updated} timesheet(s) reverted to Draft.")


# =============================================================================
# PERIOD REPORTS
# =============================================================================


class PeriodReportLineInline(admin.TabularInline):
    model = PeriodReportLine
    extra = 0
    fields = ["activity_name_snapshot", "grant_code_snapshot", "classification_snapshot", "total_hours", "percentage", "duties_description"]
    readonly_fields = ["activity_name_snapshot", "grant_code_snapshot", "classification_snapshot", "total_hours", "percentage"]


@admin.register(PeriodReport)
class PeriodReportAdmin(admin.ModelAdmin):
    list_display = ["staff", "period", "status", "total_hours", "generated_at"]
    list_filter = ["status", "period__staff_type"]
    search_fields = ["staff__user__first_name", "staff__user__last_name"]
    readonly_fields = ["generated_at", "supervisor_name_snapshot", "employee_title_snapshot", "employee_name_snapshot"]
    inlines = [PeriodReportLineInline]
    actions = ["reinitialize_report"]

    @admin.action(description="Re-initialize rollup for selected reports (recomputes lines)")
    def reinitialize_report(self, request, queryset):
        for report in queryset:
            initialize_period_report(report.staff, report.period)
        self.message_user(request, f"Re-initialized {queryset.count()} report(s).")


@admin.register(PDFSnapshot)
class PDFSnapshotAdmin(admin.ModelAdmin):
    list_display = ["__str__", "pdf_type", "version", "generated_by", "generated_at", "file_link"]
    list_filter = ["pdf_type"]
    readonly_fields = ["checksum", "generated_at", "version"]

    def file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">Download</a>', obj.file.url)
        return "—"
    file_link.short_description = "File"


# =============================================================================
# DIRECTOR EFFORT REPORTING
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


class DirectorSubmissionLineInline(admin.TabularInline):
    model = DirectorSubmissionLine
    extra = 0
    fields = ["category", "grant_code", "slot", "percentage", "is_locked"]
    readonly_fields = ["is_locked"]


@admin.register(DirectorPeriodSubmission)
class DirectorPeriodSubmissionAdmin(admin.ModelAdmin):
    list_display = ["staff", "period", "status", "submitted_at"]
    list_filter = ["status"]
    search_fields = ["staff__user__first_name", "staff__user__last_name"]
    readonly_fields = ["submitted_at", "created_at", "updated_at",
                       "employee_name_snapshot", "supervisor_name_snapshot", "employee_title_snapshot"]
    inlines = [DirectorSubmissionLineInline]
    actions = ["unlock_to_draft"]

    @admin.action(description="Unlock selected submissions back to Draft")
    def unlock_to_draft(self, request, queryset):
        updated = queryset.update(status=DirectorPeriodSubmission.Status.DRAFT, submitted_at=None)
        self.message_user(request, f"{updated} submission(s) reverted to Draft.")
