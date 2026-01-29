from django.core.management.base import BaseCommand
from cms.models import Page, PageContent
from django.contrib.sites.models import Site


class Command(BaseCommand):
    help = 'Clean up orphaned CMS pages from old sites (Site 3)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--site-id',
            type=int,
            default=3,
            help='Site ID to clean up (default: 3)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation prompt',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        site_id = options['site_id']

        try:
            site = Site.objects.get(id=site_id)
            self.stdout.write(f"Target site: {site.name} ({site.domain})")
        except Site.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Site with ID {site_id} does not exist"))
            return

        # Get all pages from the target site
        orphaned_pages = Page.objects.filter(site_id=site_id)
        total_pages = orphaned_pages.count()

        self.stdout.write(f"\nFound {total_pages} pages on Site {site_id}")

        if total_pages == 0:
            self.stdout.write(self.style.SUCCESS("No pages to clean up!"))
            return

        # Show details
        self.stdout.write("\nPages to be deleted:")
        for page in orphaned_pages:
            content_count = PageContent.objects.filter(page=page).count()
            self.stdout.write(
                f"  - Page {page.id}: path={page.path}, "
                f"reverse_id={page.reverse_id}, "
                f"content_count={content_count}"
            )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"\n[DRY RUN] Would delete {total_pages} pages. "
                    "Run without --dry-run to actually delete."
                )
            )
            return

        # Confirm deletion (unless --force is used)
        force = options.get('force', False)
        if not force:
            confirm = input(
                f"\nAre you sure you want to delete {total_pages} pages "
                f"from Site {site_id} ({site.name})? [y/N]: "
            )

            if confirm.lower() != 'y':
                self.stdout.write(self.style.WARNING("Aborted."))
                return

        # Delete pages
        deleted_count, _ = orphaned_pages.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✓ Successfully deleted {deleted_count} orphaned pages from Site {site_id}"
            )
        )
