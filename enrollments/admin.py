from django.contrib import admin
from .models import Enrollment
from people.models import People

# Register your models here.


@admin.register(Enrollment)
class EnrollmentsAdmin(admin.ModelAdmin):
    list_display = (
        "person__first_name",
        "first_name",
        "last_name",
        "workshop",
        "accepted_at",
    )
    search_fields = ("first_name", "last_name")
