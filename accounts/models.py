from django.conf import settings
from django.db import models
from people.models import People


class UserProfile(models.Model):
    """
    Links Django User accounts to People records from participant database.

    Flow:
    1. User signs in with ORCID OAuth
    2. We look up their ORCID in People table
    3. Create User account + UserProfile linking them together
    4. User can now access their profile, enrollments, etc.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        help_text="Django user account (handles authentication)",
    )
    person = models.OneToOneField(
        People,
        on_delete=models.PROTECT,
        related_name="user_profile",
        help_text="Links to migrated People record (read-only data)",
    )

    # Email verification for security
    email_verified = models.BooleanField(
        default=False, help_text="Whether user verified email matches People record"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    last_login_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_profile"
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"{self.user.username} → {self.person}"

    @property
    def orcid(self):
        """Get ORCID from linked People record"""
        return self.person.orcid_id

    @property
    def email(self):
        """Get email from linked People record"""
        return self.person.email_address
