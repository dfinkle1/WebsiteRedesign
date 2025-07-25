from django.contrib import admin
from .models import OldWorkshop, Uniqueuser
from participants.models import Participant
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from datetime import date
import csv
from django.http import HttpResponse
from .forms import EmailParticipantsForm
from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages


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


class OldWorkshopAdmin(admin.ModelAdmin):
    list_display = (
        "workshopname",
        "workshopstartdate",
        "workshopenddate",
        "participants_list",
    )
    search_fields = ("workshopid",)
    actions = ["email_participants", "export_participants_csv"]
    inlines = [ParticipantChoiceField]

    def email_participants(self, request, queryset):
        """
        Custom admin action to email all participants of selected workshops.
        """
        if "apply" in request.POST:
            form = EmailParticipantsForm(request.POST)
            if form.is_valid():
                subject = form.cleaned_data["subject"]
                message = form.cleaned_data["message"]

                # Collect all participant emails from selected workshops
                emails = []
                for workshop in queryset:
                    participants = Participant.objects.filter(workshop=workshop)
                    emails.extend(
                        [p.emailaddress for p in participants if p.emailaddress]
                    )

                emails = list(set(emails))  # remove duplicates

                if emails:
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,  # configure this in settings.py
                        emails,
                    )
                    self.message_user(
                        request, f"Successfully emailed {len(emails)} participants."
                    )
                else:
                    self.message_user(
                        request,
                        "No participants with email addresses found.",
                        level="error",
                    )

                return redirect(request.get_full_path())
        else:
            form = EmailParticipantsForm()

        return render(
            request,
            "email_participants.html",
            {"form": form, "workshops": queryset},
        )

    email_participants.short_description = "Email participants of selected workshops"

    def export_participants_csv(self, request, queryset):
        """
        Export participants from selected workshops as a CSV file.
        """
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="participants.csv"'

        writer = csv.writer(response)
        writer.writerow(["First Name", "Last Name", "Email", "Workshop"])

        for workshop in queryset:
            participants = Participant.objects.filter(workshop=workshop)
            for p in participants:
                writer.writerow(
                    [p.firstname, p.lastname, p.emailaddress, workshop.workshopname]
                )

        return response

    export_participants_csv.short_description = "Export participants as CSV"


admin.site.register(OldWorkshop, OldWorkshopAdmin)


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
