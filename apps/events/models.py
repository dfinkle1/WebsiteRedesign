from decimal import Decimal
from urllib.parse import urlencode

from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from filer.fields.image import FilerImageField


class EventManager(models.Manager):
    """Manager for published events."""

    def published(self):
        return self.filter(status=Event.Status.PUBLISHED)

    def upcoming(self):
        return self.published().filter(start__gte=timezone.now()).order_by("start")

    def past(self):
        return self.published().filter(start__lt=timezone.now()).order_by("-start")


class Event(models.Model):
    """Events such as public lectures, workshops, conferences, and social gatherings."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        CANCELLED = "cancelled", "Cancelled"
        POSTPONED = "postponed", "Postponed"

    class EventType(models.TextChoices):
        LECTURE = "lecture", "Public Lecture"
        WORKSHOP = "workshop", "Workshop"
        CONFERENCE = "conference", "Conference"
        SOCIAL = "social", "Social Event"
        WEBINAR = "webinar", "Webinar"
        OTHER = "other", "Other"

    # Core
    title = models.CharField(max_length=225)
    slug = models.SlugField(unique=True, blank=True)
    event_type = models.CharField(
        max_length=20,
        choices=EventType.choices,
        default=EventType.OTHER,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )

    # Timing
    start = models.DateTimeField()
    end = models.DateTimeField(null=True, blank=True)

    # Location
    is_online = models.BooleanField(
        default=False,
        help_text="Check if this is a virtual/online event.",
    )
    online_url = models.URLField(
        blank=True,
        help_text="Zoom, Google Meet, or other virtual event link.",
    )
    venue_name = models.CharField(max_length=200, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=120, blank=True)
    region = models.CharField(max_length=120, blank=True, help_text="State/Province")
    country = models.CharField(max_length=120, blank=True)

    # Content
    image = FilerImageField(
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="events",
    )
    short_summary = models.TextField(
        blank=True,
        max_length=300,
        help_text="Brief description for list views (max 300 chars).",
    )
    description_html = models.TextField(
        blank=True,
        help_text="Full event description (HTML allowed).",
    )

    # Tickets & Registration
    is_free = models.BooleanField(default=True)
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Ticket price (leave blank if free).",
    )
    external_ticket_url = models.URLField(
        blank=True,
        help_text="External ticketing link (Eventbrite, etc.).",
    )
    capacity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum attendees (leave blank for unlimited).",
    )
    registration_required = models.BooleanField(
        default=False,
        help_text="Require registration even for free events.",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = EventManager()

    class Meta:
        ordering = ["-start"]
        indexes = [
            models.Index(fields=["status", "start"]),
            models.Index(fields=["event_type", "start"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)[:50]
            slug = base_slug
            counter = 1
            while Event.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("events:event-detail", kwargs={"slug": self.slug})

    @property
    def is_past(self):
        """True if the event has ended."""
        end = self.end or self.start
        return end < timezone.now()

    @property
    def is_upcoming(self):
        """True if the event hasn't started yet."""
        return self.start > timezone.now()

    @property
    def is_happening_now(self):
        """True if the event is currently in progress."""
        now = timezone.now()
        end = self.end or self.start
        return self.start <= now <= end

    @property
    def full_address(self):
        """Formatted full address string."""
        parts = [self.venue_name, self.address, self.city]
        if self.city and self.region:
            parts.append(self.region)
        elif self.region:
            parts.append(self.region)
        if self.country:
            parts.append(self.country)
        return ", ".join(p for p in parts if p)

    @property
    def price_display(self):
        """Display price or 'Free'."""
        if self.is_free or not self.price:
            return "Free"
        return f"${self.price:.2f}"

    @property
    def google_calendar_url(self):
        """Generate 'Add to Google Calendar' link."""
        start_str = self.start.strftime("%Y%m%dT%H%M%S")
        end_dt = self.end or self.start
        end_str = end_dt.strftime("%Y%m%dT%H%M%S")

        params = {
            "action": "TEMPLATE",
            "text": self.title,
            "dates": f"{start_str}/{end_str}",
            "details": self.short_summary or "",
            "location": self.full_address if not self.is_online else self.online_url,
        }
        return f"https://calendar.google.com/calendar/render?{urlencode(params)}"

    @property
    def ical_url(self):
        """Generate iCal download link."""
        return reverse("events:event-ical", kwargs={"slug": self.slug})

    @property
    def maps_url(self):
        """Google Maps directions link."""
        if not self.address and not self.city:
            return None
        query = f"{self.venue_name} {self.address} {self.city} {self.region}".strip()
        return f"https://www.google.com/maps/search/?api=1&query={urlencode({'': query})[1:]}"
