# models.py
from django.db import models
from .validators import validate_file_type, validate_file_size


class Event(models.Model):
    name = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return f"{self.name} — {self.start_date.strftime('%B %d')} - {self.end_date.strftime('%B %d')}"


class ReimbursementForm(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    orcid = models.CharField(max_length=50)
    mailing_address = models.TextField()

    # Tax Info
    TAX_STATUS_CHOICES = [
        ("us_citizen", "I am a US Citizen"),
        ("green_card", "I have a green card"),
        ("visa_permit", "Visa/Permit"),
    ]
    VISA_TAX_CHOICES = [
        (
            "resident",
            "I do not have a green card but I am a resident for tax purposes according to the Substantial Presence Test",
        ),
        (
            "non_resident",
            "I am (or will be while at AIM) a non-resident for U.S. Tax Purposes",
        ),
    ]

    visa_tax_status = models.CharField(
        max_length=20, choices=VISA_TAX_CHOICES, blank=True, null=True
    )
    tax_status = models.CharField(max_length=20, choices=TAX_STATUS_CHOICES)
    green_card_copy = models.FileField(
        upload_to="green_cards/",
        blank=True,
        null=True,
        validators=[validate_file_type, validate_file_size],
    )

    visa_option = models.CharField(max_length=2, blank=True, null=True)
    admission_date = models.DateField(blank=True, null=True)
    visa_type = models.CharField(max_length=50, blank=True, null=True)
    most_recent_i94 = models.FileField(upload_to="i94/", blank=True, null=True)
    travel_history_i94 = models.FileField(upload_to="i94/", blank=True, null=True)
    passport_number = models.CharField(max_length=50, blank=True, null=True)
    passport_copy = models.FileField(
        upload_to="passports/",
        blank=True,
        null=True,
        validators=[validate_file_type, validate_file_size],
    )

    citizenship = models.CharField(max_length=100, blank=True, null=True)
    resident_of = models.CharField(max_length=100, blank=True, null=True)
    permanent_home_address = models.TextField(blank=True, null=True)

    signature = models.CharField(max_length=255)
    signed_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.event.name}"


class TravelExpense(models.Model):
    reimbursement_form = models.ForeignKey(
        ReimbursementForm, on_delete=models.CASCADE, related_name="expenses"
    )
    label = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="USD")
    receipt = models.FileField(
        upload_to="receipts/",
        blank=True,
        null=True,
        validators=[validate_file_type, validate_file_size],
    )

    def __str__(self):
        return f"{self.label} - {self.amount}"
