# Hand-written migration — Time & Effort system redesign
# Introduces ReportingCalendar, unifies PeriodReport (drops DirectorPeriodSubmission),
# adds supervisor/processed fields, removes period_type/staff_type from ReportingPeriod.

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


# ---------------------------------------------------------------------------
# Data migration helpers
# ---------------------------------------------------------------------------


def migrate_period_reports(apps, schema_editor):
    """
    1. Map old PeriodReport status values to the new choices.
    2. Set submission_type based on staff profile staff_type.
    """
    PeriodReport = apps.get_model("timeeffort", "PeriodReport")

    old_to_new_status = {
        "PENDING": "DRAFT",
        "DESCRIBING": "DRAFT",
        "GENERATED": "SUBMITTED",
        # Defensive: already-new values pass through unchanged
        "DRAFT": "DRAFT",
        "SUBMITTED": "SUBMITTED",
        "SUPV_APPR": "SUPV_APPR",
        "PROCESSED": "PROCESSED",
    }

    for report in PeriodReport.objects.select_related("staff"):
        new_status = old_to_new_status.get(report.status, "DRAFT")
        submission_type = "PCT" if report.staff.staff_type == "DIRECTOR" else "HOURS"
        PeriodReport.objects.filter(pk=report.pk).update(
            status=new_status,
            submission_type=submission_type,
        )


def delete_director_pdfsnapshots(apps, schema_editor):
    """Remove PDFSnapshot rows with pdf_type='DIRECTOR' before shrinking the column."""
    PDFSnapshot = apps.get_model("timeeffort", "PDFSnapshot")
    PDFSnapshot.objects.filter(pdf_type="DIRECTOR").delete()


def noop(apps, schema_editor):
    pass


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------


class Migration(migrations.Migration):

    dependencies = [
        ("timeeffort", "0007_director_submission_line_description"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ------------------------------------------------------------------
        # 1. ReportingCalendar (new singleton anchor table)
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="ReportingCalendar",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "anchor_start_date",
                    models.DateField(
                        unique=True,
                        help_text=(
                            "Start date of the first (or anchor) biweekly period. "
                            "Must fall on a Sunday or the organisation's standard week-start day. "
                            "All future and past periods are calculated from this date."
                        ),
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Reporting Calendar",
                "verbose_name_plural": "Reporting Calendar",
            },
        ),
        # ------------------------------------------------------------------
        # 2. Activity — add is_holiday_activity flag
        # ------------------------------------------------------------------
        migrations.AddField(
            model_name="activity",
            name="is_holiday_activity",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Mark exactly one activity as the AIM Holiday activity. "
                    "It will be auto-inserted at 8h on holidays."
                ),
            ),
        ),
        # ------------------------------------------------------------------
        # 3–4. ReportingPeriod — add calendar FK and period_index
        # ------------------------------------------------------------------
        migrations.AddField(
            model_name="reportingperiod",
            name="calendar",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="periods",
                to="timeeffort.reportingcalendar",
                help_text="Leave blank only for legacy periods created before the calendar was set up.",
            ),
        ),
        migrations.AddField(
            model_name="reportingperiod",
            name="period_index",
            field=models.IntegerField(
                default=0,
                help_text="Offset in 14-day units from the calendar anchor date. 0 = anchor period.",
            ),
        ),
        # ------------------------------------------------------------------
        # 5–6. ReportingPeriod — remove period_type and staff_type
        # ------------------------------------------------------------------
        migrations.RemoveField(
            model_name="reportingperiod",
            name="period_type",
        ),
        migrations.RemoveField(
            model_name="reportingperiod",
            name="staff_type",
        ),
        # ------------------------------------------------------------------
        # 7–8. ReportingPeriod — make start_date / end_date unique
        # ------------------------------------------------------------------
        migrations.AlterField(
            model_name="reportingperiod",
            name="start_date",
            field=models.DateField(unique=True),
        ),
        migrations.AlterField(
            model_name="reportingperiod",
            name="end_date",
            field=models.DateField(unique=True),
        ),
        # ------------------------------------------------------------------
        # 9. ReportingPeriod — update label help_text
        # ------------------------------------------------------------------
        migrations.AlterField(
            model_name="reportingperiod",
            name="label",
            field=models.CharField(
                max_length=100,
                help_text="Auto-generated display label, e.g. 'Jan 11 – Jan 24, 2026'.",
            ),
        ),
        # ------------------------------------------------------------------
        # 10. ReportingPeriod — add (calendar, period_index) unique_together
        # ------------------------------------------------------------------
        migrations.AlterUniqueTogether(
            name="reportingperiod",
            unique_together={("calendar", "period_index")},
        ),
        # ------------------------------------------------------------------
        # 11–12. ReportingWeek — make start_date / end_date unique
        # ------------------------------------------------------------------
        migrations.AlterField(
            model_name="reportingweek",
            name="start_date",
            field=models.DateField(unique=True),
        ),
        migrations.AlterField(
            model_name="reportingweek",
            name="end_date",
            field=models.DateField(unique=True),
        ),
        # ------------------------------------------------------------------
        # 13. ReportingWeek — update week_number help_text
        # ------------------------------------------------------------------
        migrations.AlterField(
            model_name="reportingweek",
            name="week_number",
            field=models.PositiveSmallIntegerField(help_text="1 or 2 within the period."),
        ),
        # ------------------------------------------------------------------
        # 14–15. WeeklyTimesheet — supervisor sign-off fields
        # ------------------------------------------------------------------
        migrations.AddField(
            model_name="weeklytimesheet",
            name="supervisor_approved_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="weeklytimesheet",
            name="supervisor_approved_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="supervisor_approved_timesheets",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        # ------------------------------------------------------------------
        # 16–22. PeriodReport — add new fields before data migration
        # ------------------------------------------------------------------
        # submission_type: default "HOURS" for migration; data migration corrects directors
        migrations.AddField(
            model_name="periodreport",
            name="submission_type",
            field=models.CharField(
                max_length=5,
                choices=[
                    ("HOURS", "Hours Based (Salary / Hourly)"),
                    ("PCT", "Percentage Based (Director)"),
                ],
                default="HOURS",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="periodreport",
            name="supervisor_approved_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="periodreport",
            name="supervisor_approved_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="supervisor_approved_reports",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="periodreport",
            name="processed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="periodreport",
            name="processed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="processed_reports",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="periodreport",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="periodreport",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        # ------------------------------------------------------------------
        # 23. Data migration — fix statuses and submission_type
        # ------------------------------------------------------------------
        migrations.RunPython(migrate_period_reports, noop),
        # ------------------------------------------------------------------
        # 24. PeriodReport — update status choices and narrow max_length
        # ------------------------------------------------------------------
        migrations.AlterField(
            model_name="periodreport",
            name="status",
            field=models.CharField(
                max_length=9,
                choices=[
                    ("DRAFT", "Draft"),
                    ("SUBMITTED", "Submitted"),
                    ("SUPV_APPR", "Supervisor Approved"),
                    ("PROCESSED", "Processed"),
                ],
                default="DRAFT",
            ),
        ),
        # ------------------------------------------------------------------
        # 25. PDFSnapshot — remove director_submission FK
        # ------------------------------------------------------------------
        migrations.RemoveField(
            model_name="pdfsnapshot",
            name="director_submission",
        ),
        # ------------------------------------------------------------------
        # 25b. Delete any DIRECTOR pdf snapshots before shrinking the column
        # ------------------------------------------------------------------
        migrations.RunPython(delete_director_pdfsnapshots, noop),
        # ------------------------------------------------------------------
        # 26. PDFSnapshot — remove DIRECTOR from pdf_type choices, fix max_length
        # ------------------------------------------------------------------
        migrations.AlterField(
            model_name="pdfsnapshot",
            name="pdf_type",
            field=models.CharField(
                max_length=6,
                choices=[
                    ("WEEKLY", "Weekly Report"),
                    ("FINAL", "Final Period Report"),
                ],
            ),
        ),
        # ------------------------------------------------------------------
        # 27–28. Drop director-only tables (child before parent)
        # ------------------------------------------------------------------
        migrations.DeleteModel(name="DirectorSubmissionLine"),
        migrations.DeleteModel(name="DirectorPeriodSubmission"),
    ]
