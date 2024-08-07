# Generated by Django 4.2.13 on 2024-07-23 15:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='StaffMember',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('position', models.CharField(max_length=255)),
                ('bio', models.TextField()),
                ('image', models.ImageField(upload_to='staff_images/')),
                ('more_info_link', models.URLField(blank=True, null=True)),
            ],
        ),
    ]
