from django.db import models
from django.contrib import admin
from django.utils.html import format_html


class OldWorkshop(models.Model):
    workshopid = models.AutoField(primary_key=True)
    workshopname = models.TextField()
    workshopabbrev = models.TextField()
    creationdate = models.DateTimeField(db_column="CreationDate", blank=True, null=True)
    workshopdescription = models.TextField(
        db_column="WorkshopDescription", blank=True, null=True
    )
    workshopstartdate = models.DateTimeField(
        db_column="WorkshopStartDate", blank=True, null=True
    )
    workshopenddate = models.DateTimeField(
        db_column="WorkshopEndDate", blank=True, null=True
    )
    organizer1 = models.TextField(db_column="Organizer1")
    organizeremail1 = models.TextField(db_column="OrganizerEmail1")
    organizer2 = models.TextField(db_column="Organizer2", blank=True, null=True)
    organizeremail2 = models.TextField(
        db_column="OrganizerEmail2", blank=True, null=True
    )
    organizer3 = models.TextField(db_column="Organizer3", blank=True, null=True)
    organizeremail3 = models.TextField(
        db_column="OrganizerEmail3", blank=True, null=True
    )
    organizer4 = models.TextField(db_column="Organizer4", blank=True, null=True)
    organizeremail4 = models.TextField(
        db_column="OrganizerEmail4", blank=True, null=True
    )
    organizer5 = models.TextField(db_column="Organizer5", blank=True, null=True)
    organizeremail5 = models.TextField(
        db_column="OrganizerEmail5", blank=True, null=True
    )
    organizer6 = models.TextField(db_column="Organizer6", blank=True, null=True)
    organizeremail6 = models.TextField(
        db_column="OrganizerEmail6", blank=True, null=True
    )
    organizer7 = models.TextField(db_column="Organizer7", blank=True, null=True)
    organizeremail7 = models.TextField(
        db_column="OrganizerEmail7", blank=True, null=True
    )
    organizer8 = models.TextField(db_column="Organizer8", blank=True, null=True)
    organizeremail8 = models.TextField(
        db_column="OrganizerEmail8", blank=True, null=True
    )
    organizer9 = models.TextField(db_column="Organizer9", blank=True, null=True)
    organizeremail9 = models.TextField(
        db_column="OrganizerEmail9", blank=True, null=True
    )
    webliaison = models.TextField(db_column="WebLiaison", blank=True, null=True)
    webliaisonemail = models.TextField(
        db_column="WebLiaisonEmail", blank=True, null=True
    )
    listorder = models.FloatField(db_column="ListOrder", blank=True, null=True)
    applicationstatus = models.IntegerField(
        db_column="ApplicationStatus", blank=True, null=True
    )
    applicationdeadline = models.DateTimeField(
        db_column="ApplicationDeadline", blank=True, null=True
    )
    applicationlatedeadline = models.DateTimeField(
        db_column="ApplicationLateDeadline", blank=True, null=True
    )
    organizerwebpage1 = models.TextField(
        db_column="OrganizerWebpage1", blank=True, null=True
    )
    organizerwebpage2 = models.TextField(
        db_column="OrganizerWebpage2", blank=True, null=True
    )
    organizerwebpage3 = models.TextField(
        db_column="OrganizerWebpage3", blank=True, null=True
    )
    organizerwebpage4 = models.TextField(
        db_column="OrganizerWebpage4", blank=True, null=True
    )
    organizerwebpage5 = models.TextField(
        db_column="OrganizerWebpage5", blank=True, null=True
    )
    organizerwebpage6 = models.TextField(
        db_column="OrganizerWebpage6", blank=True, null=True
    )
    organizerwebpage7 = models.TextField(
        db_column="OrganizerWebpage7", blank=True, null=True
    )
    organizerwebpage8 = models.TextField(
        db_column="OrganizerWebpage8", blank=True, null=True
    )
    organizerwebpage9 = models.TextField(
        db_column="Organi zerWebpage9", blank=True, null=True
    )
    webliaisonwebpage = models.TextField(
        db_column="WebLiaisonWebpage", blank=True, null=True
    )
    replydeadline = models.DateTimeField(
        db_column="ReplyDeadline", blank=True, null=True
    )
    correspondence = models.TextField(db_column="Correspondence", blank=True, null=True)
    workshopstatus = models.TextField(db_column="WorkshopStatus", blank=True, null=True)
    workshopplan = models.TextField(db_column="WorkshopPlan", blank=True, null=True)
    workshopemaildescription = models.TextField(
        db_column="WorkshopEmailDescription", blank=True, null=True
    )
    type = models.IntegerField(db_column="Type", blank=True, null=True)

    @admin.display
    def participants_list(self):
        return format_html('<span style="color:green"> Test</span>')

    def __str__(self):
        return "%s    (%s)" % (
            self.workshopname,
            self.workshopid,
        )

    class Meta:
        indexes = [models.Index(fields=["workshopstartdate"])]
        managed = True
        db_table = "old_workshop"


class People(models.Model):
    id = models.BigAutoField(primary_key=True)
    orcid_id = models.TextField(
        blank=True, null=True, unique=True
    )  # unique when present
    email = models.TextField(
        blank=True, null=True, unique=True
    )  # will be citext at DB level
    first_name = models.TextField(blank=True, null=True)
    last_name = models.TextField(blank=True, null=True)  # allow NULL if you want
    institution = models.TextField(blank=True, null=True)
    address_raw = models.TextField(blank=True, null=True)
    phone = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "people"


class Participant(models.Model):
    codenumber = models.IntegerField(blank=True, null=True)
    workshopcode = models.IntegerField(blank=True, null=True)
    firstname = models.CharField(max_length=255, blank=True, null=True)
    middlenames = models.CharField(max_length=255, blank=True, null=True)
    lastname = models.CharField(max_length=255, blank=True, null=True)
    namesuffix = models.CharField(max_length=255, blank=True, null=True)
    mailingaddress = models.TextField(blank=True, null=True)
    emailaddress = models.CharField(max_length=255, blank=True, null=True)
    phonenumber = models.CharField(max_length=255, blank=True, null=True)
    homepage = models.TextField(blank=True, null=True)
    affiliation = models.CharField(max_length=255, blank=True, null=True)
    nameprefix = models.CharField(max_length=255, blank=True, null=True)
    airport1 = models.CharField(max_length=255, blank=True, null=True)
    airport2 = models.CharField(max_length=255, blank=True, null=True)
    arrivalday = models.CharField(max_length=255, blank=True, null=True)
    departureday = models.CharField(max_length=255, blank=True, null=True)
    mrid = models.CharField(max_length=255, blank=True, null=True)
    mealrestriction = models.CharField(max_length=255, blank=True, null=True)
    hotelrequirement = models.CharField(max_length=255, blank=True, null=True)
    travelcomments1 = models.TextField(blank=True, null=True)
    travelcomments2 = models.TextField(blank=True, null=True)
    webpagecontribution = models.TextField(blank=True, null=True)
    orcid = models.CharField(max_length=255, blank=True, null=True)
    acceptedoffer = models.DateTimeField(blank=True, null=True)
    declinedoffer = models.DateTimeField(blank=True, null=True)
    declinedreason = models.TextField(blank=True, null=True)
    travelplans = models.TextField(blank=True, null=True)
    travelplanstatus = models.TextField(blank=True, null=True)
    funding = models.CharField(max_length=255, blank=True, null=True)
    limitsokay = models.TextField(blank=True, null=True)
    limitsinsufficient = models.TextField(blank=True, null=True)
    coverall = models.TextField(blank=True, null=True)
    coverairfare = models.TextField(blank=True, null=True)
    coverground = models.TextField(blank=True, null=True)
    fundingother = models.TextField(blank=True, null=True)
    gender = models.SmallIntegerField(blank=True, null=True)
    ethnicity = models.SmallIntegerField(blank=True, null=True)
    unused = models.TextField(blank=True, null=True)
    isorganizer = models.BooleanField(blank=True, null=True)
    workshop = models.ForeignKey(
        OldWorkshop,
        on_delete=models.CASCADE,
        null=True,  # Allow null values
        default=None,  # Default value is None
    )
    person = models.ForeignKey(
        People,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="participants",
    )

    class Meta:
        db_table = "participant"
        indexes = [
            models.Index(fields=["workshopcode"]),  # helps the backfill join
        ]
