from django.contrib import admin
from .models import StaffMember


@admin.register(StaffMember)
class StaffMemberAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "email", "is_visible", "order")
    list_filter = ("is_visible",)
    search_fields = ("name", "role", "email")
    ordering = ("order",)
