from allauth.account.signals import user_logged_in
from allauth.socialaccount.models import SocialAccount
from django.dispatch import receiver
from django.db import transaction
from people.models import People
from .models import UserProfile
import logging

logger = logging.getLogger(__name__)


@receiver(user_logged_in)
def link_orcid_to_people(sender, request, user, **kwargs):
    """
    Link ORCID OAuth login to People records.

    Flow:
    1. Extract ORCID and data from OAuth response
    2. Look for existing Person by ORCID
    3. If not found, look by email
    4. If found: Use existing Person data (from legacy system)
    5. If not found: Create new Person with OAuth data
    6. Update Django User with Person's information
    7. Create/update UserProfile linking User to Person
    """
    try:
        logger.info(f"=== user_logged_in signal fired for user: {user.username} (ID: {user.id}, email: {user.email}) ===")

        # Check if UserProfile already exists - if so, we're done
        if hasattr(user, 'profile') and user.profile:
            logger.info(f"UserProfile already exists for {user.username}, skipping signal")
            return

        # Try both "orcid" and "ORCID" - allauth stores it as uppercase
        sa = SocialAccount.objects.filter(user=user, provider__iexact="orcid").first()
        if not sa:
            logger.warning(f"No ORCID SocialAccount for user {user.username}, cannot link to People")
            return

        logger.info(f"Found ORCID SocialAccount: {sa.uid}")
        orcid_id = sa.uid
        extra_data = sa.extra_data or {}
        logger.info(f"Extra data from ORCID: {extra_data}")

        # Extract data from ORCID response
        email = extra_data.get("email") or user.email
        given_name = extra_data.get("given_name", "")
        family_name = extra_data.get("family_name", "")

        with transaction.atomic():
            person = None
            person_existed = False

            # Step 1: Try to find existing Person by ORCID
            if orcid_id:
                person = People.objects.filter(orcid_id=orcid_id).first()
                if person:
                    person_existed = True
                    logger.info(f"Found existing Person by ORCID: {person.id}")

            # Step 2: Try to find by email (legacy data might not have ORCID yet)
            if not person and email:
                person = People.objects.filter(email_address__iexact=email).first()
                if person:
                    person_existed = True
                    logger.info(f"Found existing Person by email: {person.id}")
                    # Link ORCID to this legacy record
                    if orcid_id and not person.orcid_id:
                        person.orcid_id = orcid_id
                        person.save(update_fields=["orcid_id"])
                        logger.info(f"Linked ORCID {orcid_id} to Person {person.id}")

            # Step 3: Create new Person if not found (first-time user)
            if not person:
                person = People.objects.create(
                    orcid_id=orcid_id,
                    email_address=email,
                    first_name=given_name,
                    last_name=family_name,
                )
                logger.info(f"Created new Person: {person.id}")

            # Step 4: Update Django User with Person data
            # Use Person's data as the source of truth
            user_needs_update = False
            if person.email_address and user.email != person.email_address:
                user.email = person.email_address
                user_needs_update = True

            if person.first_name and user.first_name != person.first_name:
                user.first_name = person.first_name
                user_needs_update = True

            if person.last_name and user.last_name != person.last_name:
                user.last_name = person.last_name
                user_needs_update = True

            if user_needs_update:
                user.save()
                logger.info(f"Updated User {user.username} with Person data")

            # Step 5: Create/update UserProfile
            prof, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={"person": person}
            )

            if created:
                logger.info(f"Created UserProfile for {user.username} → Person {person.id}")
            elif prof.person_id != person.id:
                # Update if person changed (shouldn't happen often)
                prof.person = person
                prof.save(update_fields=["person"])
                logger.info(f"Updated UserProfile for {user.username} → Person {person.id}")

            logger.info(
                f"ORCID login complete - User: {user.username}, "
                f"Person: {person.id}, Existed: {person_existed}"
            )

    except Exception as e:
        logger.error(f"Error in link_orcid_to_people signal: {type(e).__name__}: {str(e)}", exc_info=True)
