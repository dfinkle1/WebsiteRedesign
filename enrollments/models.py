import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone

from people.models import People


class Enrollment(models.Model):
    class Source(models.TextChoices):
        APPLICATION = "application", "Applied"
        INVITATION = "invitation", "Invited"
        STAFF = "staff", "Staff Added"

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
    source = models.CharField(
        max_length=12,
        choices=Source.choices,
        default=Source.APPLICATION,
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

    check_in_date = models.DateField(blank=True, null=True)
    check_out_date = models.DateField(blank=True, null=True)
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


def generate_invite_token():
    return secrets.token_urlsafe(32)


class ProgramInvitation(models.Model):
    """
    An invitation for someone to enroll in a program.

    Can target an existing Person record OR just an email address (for people
    who don't have accounts yet). The invitation token allows the recipient
    to accept without being logged in initially.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"

    program = models.ForeignKey(
        "programs.Program",
        on_delete=models.CASCADE,
        related_name="invitations",
    )

    # Target: existing person OR email for unknown users
    person = models.ForeignKey(
        People,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invitations",
        help_text="Link to existing person record, if known.",
    )
    email = models.EmailField(
        help_text="Email address to send invitation. Required even if person is linked."
    )

    token = models.CharField(
        max_length=64,
        unique=True,
        default=generate_invite_token,
        db_index=True,
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )

    # Who sent the invite and optional message
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_invitations",
    )
    message = models.TextField(
        blank=True,
        help_text="Optional personal message to include in the invitation email.",
    )

    # Resulting enrollment when accepted
    enrollment = models.OneToOneField(
        Enrollment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invitation",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    declined_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "program_invitation"
        indexes = [
            models.Index(fields=["program", "email"]),
            models.Index(fields=["status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["program", "email"],
                name="unique_invitation_per_program_email",
            ),
        ]

    def __str__(self):
        return f"Invitation({self.email} → {self.program_id})"

    @property
    def expires_at(self):
        """Invitation expires at the program's application deadline."""
        return self.program.application_deadline

    @property
    def is_expired(self):
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at

    @property
    def can_respond(self):
        """True if invitation can still be accepted or declined."""
        return self.status == self.Status.PENDING and not self.is_expired

    def accept(self, person, enrollment):
        """
        Mark invitation as accepted and link to the resulting enrollment.

        Args:
            person: The People record of the person accepting
            enrollment: The Enrollment record created for this acceptance
        """
        self.status = self.Status.ACCEPTED
        self.person = person
        self.enrollment = enrollment
        self.accepted_at = timezone.now()
        self.save(update_fields=["status", "person", "enrollment", "accepted_at"])

    def decline(self):
        """Mark invitation as declined."""
        self.status = self.Status.DECLINED
        self.declined_at = timezone.now()
        self.save(update_fields=["status", "declined_at"])


class InvitationEmail(models.Model):
    """
    Tracks each email sent for an invitation (initial + reminders).
    """

    invitation = models.ForeignKey(
        ProgramInvitation,
        on_delete=models.CASCADE,
        related_name="emails",
    )
    sent_at = models.DateTimeField(auto_now_add=True)
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    subject = models.CharField(max_length=255)
    body = models.TextField()

    class Meta:
        db_table = "invitation_email"
        ordering = ["-sent_at"]

    def __str__(self):
        return f"Email({self.invitation_id}, {self.sent_at})"
