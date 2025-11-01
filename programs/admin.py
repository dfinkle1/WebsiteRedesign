from django.contrib import admin
from django.utils import timezone
from .models import Program


class UpcomingFilter(admin.SimpleListFilter):
    title = "Date window"
    parameter_name = "when"

    def lookups(self, request, model_admin):
        return [("upcoming", "Upcoming"), ("past", "Past")]

    def queryset(self, request, queryset):
        today = timezone.localdate()
        if self.value() == "upcoming":
            return queryset.filter(end_date__gte=today)
        if self.value() == "past":
            return queryset.filter(end_date__lt=today)
        return queryset


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "type", "start_date", "end_date")
    list_filter = ("type", UpcomingFilter)
    search_fields = ("code", "title")
    ordering = ("start_date",)
