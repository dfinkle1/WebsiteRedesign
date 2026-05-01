from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("timeeffort", "0009_periodreportline_total_hours_nullable"),
    ]

    operations = [
        migrations.AddField(
            model_name="periodreport",
            name="submitted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
