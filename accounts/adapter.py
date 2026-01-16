# accounts/adapter.py
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.utils import user_email
from django.contrib.auth import get_user_model
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class OrcidAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """
        Called after successful auth at ORCID, before allauth decides to create a new user.
        If there's already a User with the same email, connect this social login to that user.

        IMPORTANT: Don't auto-connect to staff/admin accounts - those should remain separate.
        """
        if sociallogin.is_existing:
            return  # already connected

        email = user_email(sociallogin.user) or ""
        if not email:
            return  # nothing to match on; let normal flow continue

        try:
            existing = User.objects.get(email__iexact=email)

            # SECURITY: Don't auto-connect ORCID to admin/staff accounts
            if existing.is_staff or existing.is_superuser:
                logger.warning(
                    f"Refusing to connect ORCID to staff/admin account: {existing.username}"
                )
                return  # Force creation of new account

            logger.info(f"Found existing user with email {email}, connecting social account")
        except User.DoesNotExist:
            return  # no conflict; normal auto-signup will happen

        # Attach this social account to the existing user
        sociallogin.connect(request, existing)
        # Note: perform_login removed - let the normal allauth flow handle this
        # so that user_logged_in signal fires properly
