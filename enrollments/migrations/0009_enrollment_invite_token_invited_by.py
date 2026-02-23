# Generated manually for invite_token and invited_by fields

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('enrollments', '0008_add_invite_sent_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='enrollment',
            name='invite_token',
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text='Secure token for accept/decline links',
                max_length=64,
                null=True,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name='enrollment',
            name='invited_by',
            field=models.ForeignKey(
                blank=True,
                help_text='Staff member who sent the invitation',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='invited_enrollments',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
