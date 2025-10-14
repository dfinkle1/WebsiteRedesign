from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("workshops", "0005_delete_uniqueuser")]
    operations = [
        migrations.RunSQL("CREATE EXTENSION IF NOT EXISTS citext;"),
        migrations.CreateModel(
            name="People",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("orcid_id", models.TextField(blank=True, null=True, unique=True)),
                ("email", models.TextField(blank=True, null=True, unique=True)),
                ("first_name", models.TextField(blank=True, null=True)),
                (
                    "last_name",
                    models.TextField(blank=True, null=True),
                ),  # nullable per your choice
                ("institution", models.TextField(blank=True, null=True)),
                ("address_raw", models.TextField(blank=True, null=True)),
                ("phone", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "people"},
        ),
        # flip email column to citext (after table creation)
        migrations.RunSQL("ALTER TABLE people ALTER COLUMN email TYPE citext;"),
        # optional partial unique index for ORCID if you want to allow multiple NULLs but keep non-NULL unique
        migrations.RunSQL(
            "ALTER TABLE people DROP CONSTRAINT IF EXISTS people_orcid_id_key;"
        ),
        migrations.RunSQL(
            "CREATE UNIQUE INDEX IF NOT EXISTS people_orcid_unique_nonnull ON people(orcid_id) WHERE orcid_id IS NOT NULL;"
        ),
    ]
