from django.db import models
from django.db.models import TextField
from filer.fields.image import FilerImageField
from django.utils.text import slugify
from filer.fields.file import FilerFileField


class NewsArticle(models.Model):
    id = models.AutoField(
        primary_key=True,
    )
    title = models.CharField(max_length=255, blank=True, null=True)
    text = TextField(blank=True, null=True)
    news_image = FilerImageField(null=True, blank=True, on_delete=models.CASCADE)
    published_date = models.DateTimeField()
    featured = models.BooleanField(default=False)
    slug = models.SlugField(unique=True, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.slug:  # Automatically generate slug if it's empty
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title or "Unnamed News Article"

    class Meta:
        verbose_name = "News Article"


class Newsletter(models.Model):
    title = models.CharField(max_length=255)
    pdf_file = FilerFileField(on_delete=models.CASCADE, related_name="newsletter_pdf")
    photo = FilerImageField(
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="newsletter_photo",
    )

    class Meta:
        ordering = ["-title"]
