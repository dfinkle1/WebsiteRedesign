from django.db import models
from people.models import People


class Enrollment(models.Model):
    person = models.ForeignKey(
        People,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="enrollments",
    )
    workshop = models.ForeignKey(
        "programs.Program",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="enrollments",
    )
    first_name = models.TextField(blank=True, null=True)
    middle_name = models.TextField(blank=True, null=True)
    last_name = models.TextField(blank=True, null=True)
    email_snap = models.TextField(blank=True, null=True)
    orcid_snap = models.TextField(blank=True, null=True)
    institution = models.TextField(blank=True, null=True)
    accepted_at = models.DateTimeField(blank=True, null=True)
    declined_at = models.DateTimeField(blank=True, null=True)
    declined_reason = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    mailing_address = models.TextField(blank=True, null=True)
    phone_number = models.TextField(blank=True, null=True)

    airport1 = models.TextField(blank=True, null=True)
    airport2 = models.TextField(blank=True, null=True)
    funding = models.TextField(blank=True, null=True)
    limits_okay = models.TextField(blank=True, null=True)
    limits_insufficient = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "enrollment"
        indexes = [
            models.Index(fields=["person"]),
            models.Index(fields=["workshop"]),
        ]

    def __str__(self):
        return f"Enrollment(person={self.person_id},workshop={self.workshop_id})"
