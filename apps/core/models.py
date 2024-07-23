from django.db import models
from cms.models.fields import PlaceholderRelationField, PlaceholderField
from cms.utils.placeholder import get_placeholder_from_slot
from functools import cached_property
from cms.models import CMSPlugin
from filer.fields.image import FilerImageField


class MyModel(models.Model):
    # your fields
    placeholders = PlaceholderRelationField()

    @cached_property
    def my_placeholder(self):
        return get_placeholder_from_slot(self.placeholders, "slot_name")

    def get_template(self):
        return "templates/testtemplate.html"

    # your methods


class StaffMember(CMSPlugin):
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=255)
    bio = models.TextField()
    staff_photo = FilerImageField(
        null=True, blank=True, related_name="profile_picture", on_delete=models.CASCADE
    )
    more_info_link = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name
