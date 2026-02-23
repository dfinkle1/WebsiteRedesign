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
    # Invitation tracking (for staff-added enrollments that need confirmation)
    invite_token = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Secure token for accept/decline links",
    )
    invite_sent_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the invitation email was sent",
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invited_enrollments",
        help_text="Staff member who sent the invitation",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "enrollment"
        indexes = [
            models.Index(fields=["person"]),
            models.Index(fields=["workshop"]),
        ]

    def __str__(self):
        name = f"{self.first_name or ''} {self.last_name or ''}".strip() or self.email_snap or "Unknown"
        return f"Enrollment({name}, program={self.workshop_id})"

    @property
    def display_name(self):
        """Best available name for display."""
        if self.person:
            return f"{self.person.first_name} {self.person.last_name}".strip()
        return f"{self.first_name or ''} {self.last_name or ''}".strip() or self.email_snap

    @property
    def display_email(self):
        """Best available email for display."""
        if self.person and self.person.email_address:
            return self.person.email_address
        return self.email_snap

    @property
    def needs_invite(self):
        """True if this enrollment needs an invitation sent."""
        return (
            self.person is None
            and self.invite_sent_at is None
            and self.email_snap
        )

    @property
    def awaiting_response(self):
        """True if invite sent but no response yet."""
        return (
            self.person is None
            and self.invite_sent_at is not None
            and self.accepted_at is None
            and self.declined_at is None
        )

    @property
    def is_confirmed(self):
        """True if linked to a person account."""
        return self.person is not None

    def generate_invite_token(self):
        """Generate a secure token for invitation links."""
        if not self.invite_token:
            self.invite_token = secrets.token_urlsafe(32)
        return self.invite_token

    def send_invite(self, sent_by=None):
        """
        Mark as invited. Call this after successfully sending the email.

        Args:
            sent_by: The User who triggered the invite
        """
        from django.utils import timezone
        self.generate_invite_token()
        self.invite_sent_at = timezone.now()
        self.invited_by = sent_by
        self.save(update_fields=["invite_token", "invite_sent_at", "invited_by"])

    def accept(self, person):
        """
        Accept the enrollment and link to person.

        Args:
            person: The People record to link
        """
        from django.utils import timezone
        self.person = person
        self.accepted_at = timezone.now()
        self.save(update_fields=["person", "accepted_at", "updated_at"])

    def decline(self, reason=None):
        """
        Decline the enrollment.

        Args:
            reason: Optional reason for declining
        """
        from django.utils import timezone
        self.declined_at = timezone.now()
        if reason:
            self.declined_reason = reason
            self.save(update_fields=["declined_at", "declined_reason", "updated_at"])
        else:
            self.save(update_fields=["declined_at", "updated_at"])


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
