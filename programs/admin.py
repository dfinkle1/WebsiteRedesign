from django.contrib import admin
from .models import Program


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "start_date", "application_deadline")
    list_filter = ("start_date", "type")
    search_fields = ("code", "title")


# @admin.register(OldWorkshop)
# class OldWorkshopAdmin(admin.ModelAdmin):
#     list_display = (
#         "workshopid",
#         "workshopname",
#         "workshopstartdate",
#         "workshopenddate",
#     )
#     search_fields = ("workshopname", "workshopabbrev")
#     list_filter = ("workshopstartdate",)
#     inlines = [ParticipantInlineForWorkshop]
