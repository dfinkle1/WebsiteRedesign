# Generated by Django 5.0.8 on 2025-04-03 20:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_alter_newsarticle_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='newsarticle',
            name='slug',
            field=models.SlugField(blank=True, null=True, unique=True),
        ),
    ]
