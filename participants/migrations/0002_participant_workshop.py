# Generated by Django 4.2.13 on 2024-05-14 19:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0001_initial'),
        ('participants', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='participant',
            name='workshop',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='workshops.oldworkshop'),
        ),
    ]
