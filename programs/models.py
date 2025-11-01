from django.db import models
from django.contrib import admin
from django.utils import timezone


class ProgramQuerySet(models.QuerySet):
    def upcoming_workshops(self):
        return (
            self.filter(
                type=Program.ProgramType.WORKSHOP, start_date__gte=timezone.localdate()
            )
            .select_related("location", "organizer")
            .only("title", "code", "application_deadline", "start_date", "end_date")
        )


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
    abbreviation = models.CharField(max_length=255, blank=True, null=True)
    organizer1 = models.CharField(max_length=255, null=True)
    organizeremail1 = models.CharField(max_length=255, null=True)
    organizer2 = models.CharField(max_length=255, null=True)
    organizeremail2 = models.CharField(max_length=255, null=True)
    organizer3 = models.CharField(max_length=255, null=True)
    organizeremail3 = models.CharField(max_length=255, null=True)
    scribe = models.CharField(max_length=255, null=True)
    scribe_email = models.CharField(max_length=255, null=True)
    application_status = models.BigIntegerField(null=True)
    correspondence = models.CharField(max_length=255, null=True)
    workshop_status = models.CharField(max_length=255, null=True)
    type = models.CharField(max_length=20, choices=ProgramType.choices)
    location = models.CharField(max_length=255, null=True)
    application_deadline = models.DateTimeField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    workshop_email_description = models.CharField(max_length=255, null=True)
    online = models.BooleanField(default=True, null=True)
    objects = ProgramQuerySet.as_manager()

    class Meta:
        indexes = [models.Index(fields=["type", "start_date"])]
        db_table = "program"

    def __str__(self):
        return f"{self.code} — {self.title}"
