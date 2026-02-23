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

    def accepting_applications(self):
        """Programs currently open for public applications."""
        return self.filter(
            application_mode=Program.ApplicationMode.OPEN,
            application_deadline__gte=timezone.now(),
        )


class Program(models.Model):
    class ProgramType(models.TextChoices):
        WORKSHOP = "WORKSHOP", "Workshop"
        SQUARE = "SQUARE", "SQuaRE"
        MEETING = "MEETING", "Meeting"
        VWORKSHOP = "VWORKSHOP", "Virtual Workshop"
        VSQUARE = "VSQUARE", "Virtual SQuaRE"
        COMMUNITY = "COMMUNITY", "Community"

    class ApplicationMode(models.TextChoices):
        CLOSED = "closed", "Closed"
        OPEN = "open", "Open Applications"
        INVITE_ONLY = "invite", "Invite Only"

    class MeetingNumber(models.IntegerChoices):
        FIRST = 1, "1st Meeting"
        SECOND = 2, "2nd Meeting"
        THIRD = 3, "3rd Meeting"

    code = models.IntegerField(unique=True, blank=True)
    title = models.CharField(max_length=255)
    abbreviation = models.CharField(max_length=255, blank=True, null=True)
    organizer1 = models.CharField(max_length=255, blank=True, null=True)
    organizeremail1 = models.CharField(max_length=255, null=True)
    organizer2 = models.CharField(max_length=255, blank=True, null=True)
    organizeremail2 = models.CharField(max_length=255, blank=True, null=True)
    organizer3 = models.CharField(max_length=255, blank=True, null=True)
    organizeremail3 = models.CharField(max_length=255, blank=True, null=True)
    scribe = models.CharField(max_length=255, blank=True, null=True)
    scribe_email = models.CharField(max_length=255, blank=True, null=True)
    application_status = models.BigIntegerField(blank=True, null=True)
    correspondence = models.CharField(max_length=255, blank=True, null=True)
    workshop_status = models.CharField(max_length=255, blank=True, null=True)
    type = models.CharField(max_length=20, blank=True, choices=ProgramType.choices)
    location = models.CharField(max_length=255, blank=True, null=True)
    application_deadline = models.DateTimeField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    workshop_email_description = models.CharField(max_length=255, blank=True, null=True)
    online = models.BooleanField(default=True, blank=True, null=True)
    application_mode = models.CharField(
        max_length=10,
        choices=ApplicationMode.choices,
        default=ApplicationMode.CLOSED,
    )
    meeting_number = models.PositiveSmallIntegerField(
        choices=MeetingNumber.choices,
        blank=True,
        null=True,
        help_text="For SQuaREs: which meeting (1st, 2nd, or 3rd)",
    )
    objects = ProgramQuerySet.as_manager()

    class Meta:
        indexes = [models.Index(fields=["type", "start_date"])]
        db_table = "program"

    def save(self, *args, **kwargs):
        if not self.code:
            # Get the maximum existing code and add 1
            max_code = Program.objects.aggregate(models.Max("code"))["code__max"]
            self.code = (max_code or 0) + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} — {self.title}"

    @property
    def is_accepting_applications(self):
        """True if program has open applications and deadline hasn't passed."""
        if self.application_mode != self.ApplicationMode.OPEN:
            return False
        if not self.application_deadline:
            return False
        return timezone.now() <= self.application_deadline

    @property
    def applications_closed(self):
        """True if application deadline has passed or mode is closed."""
        if self.application_mode == self.ApplicationMode.CLOSED:
            return True
        if self.application_deadline and timezone.now() > self.application_deadline:
            return True
        return False


# =============================================================================
# PROXY MODELS FOR ADMIN
# These don't create new database tables - they're just filtered views
# =============================================================================


class WorkshopManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(type=Program.ProgramType.WORKSHOP)


class Workshop(Program):
    """Proxy model for Workshops - appears as separate admin entry."""
    objects = WorkshopManager()

    class Meta:
        proxy = True
        verbose_name = "Workshop"
        verbose_name_plural = "Workshops"


class SQuaREManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(type=Program.ProgramType.SQUARE)


class SQuaRE(Program):
    """Proxy model for SQuaREs - appears as separate admin entry."""
    objects = SQuaREManager()

    class Meta:
        proxy = True
        verbose_name = "SQuaRE"
        verbose_name_plural = "SQuaREs"


class ResearchCommunityManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(type=Program.ProgramType.COMMUNITY)


class ResearchCommunity(Program):
    """Proxy model for Research Communities."""
    objects = ResearchCommunityManager()

    class Meta:
        proxy = True
        verbose_name = "Research Community"
        verbose_name_plural = "Research Communities"
