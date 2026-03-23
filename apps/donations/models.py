from django.db import models
from django.utils import timezone


class DonationCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name_plural = "donation categories"

    def __str__(self):
        return self.name


class OrganizationSettings(models.Model):
    """
    Singleton — one row only. Staff update EIN/legal name from admin without a code deploy.
    """

    legal_name = models.CharField(max_length=200, default="American Institute of Mathematics")
    ein = models.CharField(max_length=20, default="", help_text="e.g. 20-1715007")
    address_line1 = models.CharField(max_length=200, blank=True)
    address_line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=2, blank=True)
    zip_code = models.CharField(max_length=10, blank=True)
    receipt_footer = models.TextField(
        blank=True,
        help_text="Extra text appended to all receipt emails (e.g. legal boilerplate).",
    )

    class Meta:
        verbose_name = "organization settings"
        verbose_name_plural = "organization settings"

    def __str__(self):
        return self.legal_name

    @classmethod
    def get(cls):
        """Always returns the single settings row, creating it if needed."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Donation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"
        CANCELLED = "cancelled", "Cancelled"

    # Donor
    donor_name = models.CharField(max_length=200)
    donor_email = models.EmailField()

    # Amount
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")

    # Category
    category = models.ForeignKey(
        DonationCategory,
        on_delete=models.PROTECT,
        related_name="donations",
    )

    # PayPal
    paypal_order_id = models.CharField(max_length=100, blank=True, db_index=True)
    paypal_capture_id = models.CharField(max_length=100, blank=True)

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    # Receipt
    receipt_number = models.CharField(max_length=30, blank=True, unique=True, null=True)
    receipt_sent_at = models.DateTimeField(null=True, blank=True)

    # Tax compliance
    goods_or_services_provided = models.BooleanField(
        default=False,
        help_text="Set True only if the donor received something of value in exchange.",
    )

    # Internal
    notes = models.TextField(blank=True, help_text="Internal staff notes.")
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.donor_name} — ${self.amount} ({self.get_status_display()})"

    @property
    def is_tax_deductible(self):
        return not self.goods_or_services_provided


class WebhookEvent(models.Model):
    """
    Raw log of every PayPal webhook received.
    Critical for auditing and debugging — never delete these.
    """

    paypal_event_id = models.CharField(max_length=100, unique=True)
    event_type = models.CharField(max_length=100)
    raw_body = models.TextField()
    received_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ["-received_at"]

    def __str__(self):
        return f"{self.event_type} — {self.paypal_event_id}"
