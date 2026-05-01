from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("timeeffort", "0008_reporting_calendar_unified_periods"),
    ]

    operations = [
        migrations.AlterField(
            model_name="periodreportline",
            name="total_hours",
            field=models.DecimalField(
                max_digits=7,
                decimal_places=2,
                null=True,
                blank=True,
            ),
        ),
    ]
