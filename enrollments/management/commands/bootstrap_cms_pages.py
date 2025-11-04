from django.core.management.base import BaseCommand, CommandError
from django.contrib.sites.models import Site
from django.contrib.auth import get_user_model

from cms.api import create_page
from cms.models import Page

try:
    from djangocms_versioning.models import Version
    from djangocms_versioning.constants import DRAFT

    HAS_VERSIONING = True
except ImportError:
    HAS_VERSIONING = False


class Command(BaseCommand):
    help = "Create AIM base django CMS pages if they don't exist."

    def handle(self, *args, **options):
        site = Site.objects.get_current()
        User = get_user_model()

        # use first superuser as the "creator" of the pages
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            raise CommandError(
                "No superuser found. Run `python manage.py createsuperuser` first."
            )

        pages = [
            {
                "title": "Home",
                "slug": "",
                "reverse_id": "home",
                "template": "cms_templates/home.html",
                "in_navigation": False,
            },
            {
                "title": "About",
                "slug": "about",
                "reverse_id": "about",
                "template": "cms_templates/about.html",
                "in_navigation": True,
            },
            {
                "title": "Focused Collaborative Research",
                "slug": "focused-collaborative-research",
                "reverse_id": "collaborative",
                "template": "cms_templates/focused-landing.html",
                "in_navigation": True,
            },
            {
                "title": "Joyful Mathematics for All",
                "slug": "joyful-mathematics-for-all",
                "reverse_id": "joyful",
                "template": "cms_templates/joyfulmathematics.html",
                "in_navigation": True,
            },
            {
                "title": "Visiting",
                "slug": "visiting",
                "reverse_id": "visiting",
                "template": "cms_templates/visiting.html",
                "in_navigation": True,
            },
            {
                "title": "Resources",
                "slug": "resources",
                "reverse_id": "resources",
                "template": "cms_templates/resources.html",
                "in_navigation": True,
            },
            {
                "title": "News",
                "slug": "news",
                "reverse_id": "news",
                "template": "cms_templates/news.html",
                "in_navigation": True,
            },
            {
                "title": "FRG",
                "slug": "frg",
                "reverse_id": "frg",
                # 🔴 NOTE: must match CMS_TEMPLATES first element exactly!
                "template": "FRG/frg-landing.html",
                "in_navigation": True,
            },
        ]

        for cfg in pages:
            if Page.objects.filter(site=site, reverse_id=cfg["reverse_id"]).exists():
                self.stdout.write(
                    f"Page '{cfg['reverse_id']}' already exists, skipping."
                )
                continue

            page = create_page(
                title=cfg["title"],
                slug=cfg["slug"],
                template=cfg["template"],
                language="en",
                reverse_id=cfg["reverse_id"],
                in_navigation=cfg.get("in_navigation", True),
                site=site,
                created_by=user,  # 👈 important for versioning
            )

            # If versioning is installed, auto-publish the created draft
            if HAS_VERSIONING:
                version = (
                    Version.objects.filter_by_grouper(page).filter(state=DRAFT).first()
                )
                if version:
                    version.publish(user)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Created page '{cfg['reverse_id']}' at '/{cfg['slug'] or ''}' "
                    f"using template '{cfg['template']}'"
                )
            )
