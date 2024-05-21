from django.db import models
from workshops.models import OldWorkshop


class Participant(models.Model):
    codenumber = models.IntegerField(blank=True, null=True)
    workshopcode = models.IntegerField()
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

    def __str__(self):
        return str(self.id)

    class Meta:
        managed = True
        db_table = "participant"
