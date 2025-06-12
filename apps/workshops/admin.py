from django.contrib import admin
from .models import OldWorkshop, Uniqueuser
from participants.models import Participant
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from datetime import date


class WorkshopDateFilter(admin.SimpleListFilter):
    title = _("Workshop Date")
    parameter_name = "workshop_date"

    def lookups(self, request, model_admin):
        # Define the filter options here
        return (
            ("past", _("Past Workshops")),
            ("future", _("Future Workshops")),
        )

    def queryset(self, request, queryset):
        current_date = date.today()
        # Apply the filter based on the selected option
        if self.value() == "past":
            return queryset.filter(workshopstartdate__lte=current_date)
        elif self.value() == "future":
            return queryset.filter(workshopstartdate__gt=current_date)


admin.site.site_header = "AIM Admin"


class ParticipantChoiceField(admin.TabularInline):
    model = Participant
    fields = [
        "firstname",
        "lastname",
        "emailaddress",
    ]  # Customize fields displayed in dropdown
    extra = 0
    can_delete = False


@admin.register(OldWorkshop)
class OldWorkshopAdmin(admin.ModelAdmin):

    list_display = [
        "workshopname",
        "workshopid",
        # "get_participant_list",
        "participants_list",
    ]
    inlines = [ParticipantChoiceField]
    search_fields = ["workshopid"]
    list_filter = [WorkshopDateFilter]

    # def get_participant_list(self, obj):
    #     if obj.participant_list:
    #         return obj.participant_list
    #     else:
    #         return "Not Available"

    # get_participant_list.short_description = "Ballers"

    # raw_id_fields = [ParticipantInline]
    # autocomplete_fields = [ParticipantInline]

    # def view_participants(self, request, queryset):
    #     workshop_ids = queryset.values_list("id", flat=True)
    #     url = (
    #         reverse("admin:view_participants")
    #         + "?workshop_ids="
    #         + ",".join(map(str, workshop_ids))
    #     )
    #     return HttpResponseRedirect(url)

    # view_participants.short_description = "View Participants"

    # actions = [view_participants]




@admin.register(Uniqueuser)
class UniqueuserAdmin(admin.ModelAdmin):
    list_display = [
        "personid",
        "firstname",
        "lastname",
        "workshopcode",
    ]  # Customize the displayed fields

    search_fields = [
        "firstname",
        "lastname",
    ]  # Enable search functionality based on first name and last name


