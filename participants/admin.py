from django.contrib import admin
from .models import Participant


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    def display_is_organizer(self):
        if self.isorganizer == True:
            return "Is organizer"
        else:
            return "Not Organizer"

    list_display = [
        "id",
        "firstname",
        "lastname",
        "workshopcode",
        "namesuffix",
        display_is_organizer,
        "isorganizer",
    ]
    search_fields = [
        "firstname",
        "lastname",
    ]


