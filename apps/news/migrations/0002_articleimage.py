# Generated manually - add ArticleImage model for galleries

import django.db.models.deletion
from django.db import migrations, models
import filer.fields.image


class Migration(migrations.Migration):

    dependencies = [
        ("filer", "0001_initial"),
        ("news", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ArticleImage",
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
                    "caption",
                    models.CharField(
                        blank=True,
                        help_text="Optional caption displayed below the image.",
                        max_length=255,
                    ),
                ),
                (
                    "order",
                    models.PositiveSmallIntegerField(
                        default=0,
                        help_text="Order in gallery (lower numbers appear first).",
                    ),
                ),
                (
                    "article",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="images",
                        to="news.newsarticle",
                    ),
                ),
                (
                    "image",
                    filer.fields.image.FilerImageField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="article_images",
                        to="filer.image",
                    ),
                ),
            ],
            options={
                "verbose_name": "Article Image",
                "verbose_name_plural": "Article Images",
                "ordering": ["order", "id"],
            },
        ),
    ]
