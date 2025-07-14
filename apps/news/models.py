from django.db import models
from filer.fields.image import FilerImageField
from djangocms_text_ckeditor.fields import HTMLField
from django.utils.text import slugify


class NewsArticle(models.Model):
    id = models.AutoField(
        primary_key=True,
    )
    title = models.CharField(max_length=255, blank=True, null=True)
    text = HTMLField(blank=True, null=True)
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
