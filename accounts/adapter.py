# accounts/adapter.py
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.utils import perform_login, user_email
from django.contrib.auth import get_user_model

User = get_user_model()


class OrcidAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """
        Called after successful auth at ORCID, before allauth decides to create a new user.
        If there's already a User with the same email, connect this social login to that user.
        """
        if sociallogin.is_existing:
            return  # already connected

        email = user_email(sociallogin.user) or ""
        if not email:
            return  # nothing to match on; let normal flow continue

        try:
            existing = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return  # no conflict; normal auto-signup will happen

        # Attach this social account to the existing user
        sociallogin.connect(request, existing)

        # Log in as the existing user (aborts the “create new user” path)
        perform_login(request, existing, email_verification="optional")
