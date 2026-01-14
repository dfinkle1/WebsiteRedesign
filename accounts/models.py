from django.conf import settings
from django.db import models
from people.models import People


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    person = models.ForeignKey(People, on_delete=models.PROTECT)
    orcid = models.CharField(
        max_length=19, blank=True, null=True
    )  # mirror People.orcid_id (e.g., 0000-0002-1825-0097)

    email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "person")]
