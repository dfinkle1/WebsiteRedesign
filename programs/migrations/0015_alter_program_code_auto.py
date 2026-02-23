# Generated manually - make code field auto-incrementing

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('programs', '0014_program_meeting_number'),
    ]

    operations = [
        migrations.AlterField(
            model_name='program',
            name='code',
            field=models.IntegerField(blank=True, unique=True),
        ),
    ]
