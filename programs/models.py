from django.db import models
from django.contrib import admin
from django.utils import timezone


class ProgramQuerySet(models.QuerySet):
    def upcoming_workshops(self):
        return (
            self.filter(
                type=Program.ProgramType.WORKSHOP, start_date__gte=timezone.localdate()
            )
            .only("title", "code", "application_deadline", "start_date", "end_date")
        )

    def accepting_applications(self):
        """Programs currently open for public applications."""
        return self.filter(
            application_mode=Program.ApplicationMode.OPEN,
            application_deadline__gte=timezone.now(),
        )

    def completed_squares(self):
        """
        SQuaREs that have completed their final meeting.
        Returns the root (meeting 1) of each completed SQuaRE group.
        """
        today = timezone.localdate()
        # Get all SQuaRE meetings that have ended
        return self.filter(
            type=Program.ProgramType.SQUARE,
            end_date__lt=today,
            parent_square__isnull=True,  # Only root meetings
        ).order_by('-end_date')


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
        FOURTH = 4, "4th Meeting"
        FIFTH = 5, "5th Meeting"

    code = models.IntegerField(unique=True, blank=True)

    # Link SQuaRE meetings together (meeting 2/3/4/5 points to meeting 1)
    parent_square = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subsequent_meetings',
        help_text="For SQuaRE meetings 2-5: link to the 1st meeting of this SQuaRE group.",
    )
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
        help_text="For SQuaREs: which meeting (1st through 5th)",
    )
    objects = ProgramQuerySet.as_manager()

    # -------------------------------------------------------------------------
    # SQuaRE-specific properties
    # -------------------------------------------------------------------------

    @property
    def is_square(self):
        """True if this is a SQuaRE program."""
        return self.type in [self.ProgramType.SQUARE, self.ProgramType.VSQUARE]

    @property
    def square_root(self):
        """
        Get the root (1st meeting) of this SQuaRE group.
        Returns self if this is already the root.
        """
        if self.parent_square:
            return self.parent_square
        return self

    @property
    def all_square_meetings(self):
        """
        Get all meetings in this SQuaRE group (including self).
        Returns queryset ordered by meeting number.
        """
        root = self.square_root
        # Get root + all subsequent meetings
        meetings = Program.objects.filter(
            models.Q(pk=root.pk) | models.Q(parent_square=root)
        ).order_by('meeting_number', 'start_date')
        return meetings

    @property
    def latest_meeting(self):
        """Get the most recent meeting in this SQuaRE group."""
        return self.all_square_meetings.order_by('-meeting_number', '-start_date').first()

    @property
    def is_square_complete(self):
        """
        True if this SQuaRE has completed (latest meeting has ended).
        """
        if not self.is_square:
            return False
        latest = self.latest_meeting
        if not latest or not latest.end_date:
            return False
        return latest.end_date < timezone.localdate()

    def get_all_square_participants(self):
        """
        Get all unique participants across all meetings of this SQuaRE.
        Returns a queryset of People objects.
        """
        from people.models import People
        from enrollments.models import Enrollment

        # Get all meeting IDs in this SQuaRE group
        meeting_ids = self.all_square_meetings.values_list('id', flat=True)

        # Get unique person IDs from enrollments across all meetings
        person_ids = Enrollment.objects.filter(
            workshop_id__in=meeting_ids,
            person__isnull=False,
        ).values_list('person_id', flat=True).distinct()

        return People.objects.filter(id__in=person_ids).order_by('last_name', 'first_name')

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
