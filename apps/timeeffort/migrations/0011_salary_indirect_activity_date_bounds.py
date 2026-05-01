from decimal import Decimal

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("timeeffort", "0010_periodreport_submitted_at"),
    ]

    operations = [
        # Activity: add valid_from / valid_to date bounds
        migrations.AddField(
            model_name="activity",
            name="valid_from",
            field=models.DateField(
                blank=True,
                null=True,
                help_text="First date this activity (grant) is valid. Leave blank for no start restriction.",
            ),
        ),
        migrations.AddField(
            model_name="activity",
            name="valid_to",
            field=models.DateField(
                blank=True,
                null=True,
                help_text="Last date this activity (grant) is valid. Leave blank for no end restriction.",
            ),
        ),
        # WeeklyTimesheetLine: make activity nullable and add custom_activity_name
        migrations.AlterField(
            model_name="weeklytimesheetline",
            name="activity",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="timesheet_lines",
                to="timeeffort.activity",
            ),
        ),
        migrations.AddField(
            model_name="weeklytimesheetline",
            name="custom_activity_name",
            field=models.CharField(
                blank=True,
                max_length=255,
                help_text="Free-text activity name for custom grant rows (salary staff only).",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="weeklytimesheetline",
            unique_together=set(),
        ),
        # SalaryIndirectAllocation
        migrations.CreateModel(
            name="SalaryIndirectAllocation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("hours_administrative", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=5)),
                ("hours_other_activity", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=5)),
                ("hours_sick_personal", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=5)),
                ("hours_vacation", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=5)),
                ("hours_fundraising_pr", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=5)),
                ("hours_other_unallowable", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=5)),
                (
                    "profile",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="salary_indirect",
                        to="timeeffort.stafftimesheetprofile",
                    ),
                ),
            ],
            options={
                "verbose_name": "Salary Indirect Allocation",
                "verbose_name_plural": "Salary Indirect Allocations",
            },
        ),
    ]
