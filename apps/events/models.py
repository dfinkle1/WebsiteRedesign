from django.db import models
from django.db.models import TextField
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from filer.fields.image import FilerImageField


# Create your models here.
class Event(models.Model):
    id = models.AutoField(
        primary_key=True,
    )
    title = models.CharField(max_length=225)
    slug = models.SlugField(unique=True, blank=True)
    start = models.DateTimeField()
    end = models.DateTimeField(null=True, blank=True)

    venue_name = models.CharField(max_length=200, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=120, blank=True)
    region = models.CharField(max_length=120, blank=True)
    country = models.CharField(max_length=120, blank=True)

    image = FilerImageField(null=True, blank=True, on_delete=models.SET_NULL)
    short_summary = models.TextField(blank=True)
    description_html = models.TextField(blank=True)  # or use a CMS placeholder
    external_ticket_url = models.URLField(blank=True)

    class Meta:
        ordering = ["-start"]

    @property
    def is_past(self):
        end = self.end or self.start
        return end < timezone.now()
