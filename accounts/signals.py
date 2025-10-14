from allauth.account.signals import user_logged_in
from allauth.socialaccount.models import SocialAccount
from django.dispatch import receiver
from django.db import transaction
from apps.workshops.models import People
from .models import UserProfile


@receiver(user_logged_in)
def link_orcid_to_people(sender, request, user, **kwargs):
    sa = SocialAccount.objects.filter(user=user, provider="orcid").first()
    orcid_id = sa.uid if sa else None
    email = (sa.extra_data or {}).get("email") if sa else (user.email or None)

    with transaction.atomic():
        person = None
        if orcid_id:
            person = People.objects.filter(orcid_id=orcid_id).first()
        if not person and email:
            person = People.objects.filter(email__iexact=email).first()
            if person and orcid_id and not person.orcid_id:
                person.orcid_id = orcid_id
                person.save(update_fields=["orcid_id"])
        if not person:
            person = People.objects.create(orcid_id=orcid_id, email=email)

        prof, _ = UserProfile.objects.get_or_create(
            user=user, defaults={"person": person, "orcid": orcid_id}
        )
        if prof.person_id != person.id or (orcid_id and prof.orcid != orcid_id):
            prof.person = person
            if orcid_id:
                prof.orcid = orcid_id
            prof.save(update_fields=["person", "orcid"])
