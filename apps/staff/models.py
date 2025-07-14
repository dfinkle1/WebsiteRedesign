from django.db import models
from filer.fields.image import FilerImageField
from djangocms_text_ckeditor.fields import HTMLField


class StaffMember(models.Model):
    name = models.CharField(max_length=255, blank=True, null=True)
    role = models.CharField(max_length=255, blank=True, null=True)
    bio = HTMLField(blank=True, null=True)
    staff_photo = FilerImageField(null=True, blank=True, on_delete=models.CASCADE)
    email = models.CharField(max_length=255, blank=True, null=True)
    more_info_link = models.URLField(blank=True, null=True)
    is_visible = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name or "Unnamed Staff Member"
