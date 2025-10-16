from django.db import models


class People(models.Model):
    first_name = models.TextField(blank=True, null=True)
    last_name = models.TextField(blank=True, null=True)  # allow NULL if you want
    preferred_name = models.TextField(blank=True, null=True)
    email_address = models.TextField(
        blank=True, null=True, unique=True
    )  # will be citext at DB level
    mailing_address = models.TextField(blank=True, null=True)
    phone_number = models.TextField(blank=True, null=True)
    orcid_id = models.TextField(
        blank=True, null=True, unique=True
    )  # unique when present
    home_page = models.TextField(blank=True, null=True)
    math_review_id = models.TextField(blank=True, null=True)
    institution = models.TextField(blank=True, null=True)
    dietary_restrictions = models.TextField(blank=True, null=True)
    gender = models.TextField(blank=True, null=True)
    ethnicity = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["last_name", "first_name"])]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
