from django.db import models
from cms.models.fields import PlaceholderRelationField, PlaceholderField
from cms.utils.placeholder import get_placeholder_from_slot
from functools import cached_property
from cms.models import CMSPlugin
from filer.fields.image import FilerImageField
from cms.models.pluginmodel import CMSPlugin
from djangocms_text_ckeditor.fields import HTMLField


class MyModel(models.Model):
    # your fields
    placeholders = PlaceholderRelationField()

    @cached_property
    def my_placeholder(self):
        return get_placeholder_from_slot(self.placeholders, "slot_name")

    # your methods


class StaffMember(CMSPlugin):
    name = models.CharField(max_length=255, blank=True, null=True)
    role = models.CharField(max_length=255, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    staff_photo = FilerImageField(
        null=True, blank=True, related_name="profile_picture", on_delete=models.CASCADE
    )
    more_info_link = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name or "Unnamed Staff Member"


class NewsArticle(CMSPlugin):
    title = models.CharField(max_length=255, blank=True, null=True)
    text = HTMLField(blank=True, null=True)
    news_image = FilerImageField(null=True, blank=True, on_delete=models.CASCADE)
    published_date = models.DateTimeField(auto_now_add=True)
    featured = models.BooleanField(default=False)

    def __str__(self):
        return self.title or "Unnamed News Article"
