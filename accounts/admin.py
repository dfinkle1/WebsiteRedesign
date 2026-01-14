from django.contrib import admin

from people.models import People
from .models import UserProfile

# Register your models here.


@admin.register(UserProfile)
class UserProfile(admin.ModelAdmin):
    list_display = (
        "user",
        "orcid",
        "email_verified",
    )
