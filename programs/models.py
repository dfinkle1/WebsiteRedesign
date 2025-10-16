from django.db import models
from django.contrib import admin
from django.utils.html import format_html


class Program(models.Model):
    class ProgramType(models.TextChoices):
        WORKSHOP = "WORKSHOP", "Workshop"
        SQUARE = "SQUARE", "SQuaRE"
        MEETING = "MEETING", "Meeting"
        VWORKSHOP = "VWORKSHOP", "Virtual Workshop"
        VSQUARE = "VSQUARE", "Virtual SQuaRE"
        COMMUNITY = "COMMUNITY", "Community"

    code = models.IntegerField(unique=True)
    title = models.CharField(max_length=255)
    title_abbreviation = models.CharField(max_length=255, blank=True, null=True)
    type = models.CharField(max_length=20, choices=ProgramType.choices)
    location = models.CharField(max_length=255, null=True)
    scribe = models.CharField(max_length=255, null=True)
    application_deadline = models.DateTimeField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    online = models.BooleanField(default=True, null=True)

    class Meta:
        indexes = [models.Index(fields=["type", "start_date"])]

    def __str__(self):
        return f"{self.code} — {self.title}"
