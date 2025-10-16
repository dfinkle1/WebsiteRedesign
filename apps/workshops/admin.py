from django.contrib import admin
from .models import OldWorkshop, Participant, People  # adjust import paths


class ParticipantInlineForWorkshop(admin.TabularInline):
    model = Participant
    extra = 0
    fields = (
        "person",
        "firstname",
        "lastname",
        "emailaddress",
        "isorganizer",
    )
    autocomplete_fields = ("person",)
    show_change_link = True


@admin.register(OldWorkshop)
class OldWorkshopAdmin(admin.ModelAdmin):
    list_display = (
        "workshopid",
        "workshopname",
        "workshopstartdate",
        "workshopenddate",
    )
    search_fields = ("workshopname", "workshopabbrev")
    list_filter = ("workshopstartdate",)
    inlines = [ParticipantInlineForWorkshop]


class ParticipantInlineForPerson(admin.TabularInline):
    model = Participant
    extra = 0
    fields = ("workshop", "isorganizer")
    autocomplete_fields = ("workshop",)
    show_change_link = True


@admin.register(People)
class PeopleAdmin(admin.ModelAdmin):
    list_display = ("id", "orcid_id", "email", "first_name", "last_name", "institution")
    search_fields = ("orcid_id", "email", "first_name", "last_name", "institution")
    inlines = [ParticipantInlineForPerson]


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "person",
        "workshop",
        "isorganizer",
        "emailaddress",
        "firstname",
        "lastname",
    )
    list_filter = ("isorganizer",)
    search_fields = (
        "firstname",
        "lastname",
        "emailaddress",
        "orcid",
        "workshop__workshopname",
        "person__email",
    )
    autocomplete_fields = ("person", "workshop")
