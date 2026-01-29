from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.utils.html import strip_tags
from filer.fields.image import FilerImageField
from filer.fields.file import FilerFileField


class ArticlePublishedManager(models.Manager):
    """Returns only published articles (respects publish date)."""

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(is_published=True, published_at__lte=timezone.now())
        )


class NewsletterPublishedManager(models.Manager):
    """Returns only published newsletters."""

    def get_queryset(self):
        return super().get_queryset().filter(is_published=True)


class NewsArticle(models.Model):
    """News stories about events, programs, and organizational updates."""

    # Core fields
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    excerpt = models.CharField(
        max_length=300,
        blank=True,
        help_text="Short summary for list pages. Auto-generated from body if blank.",
    )
    body = models.TextField(help_text="Full article content (HTML allowed)")

    # Media
    featured_image = FilerImageField(
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="news_articles",
    )

    # Metadata
    is_published = models.BooleanField(default=False, db_index=True)
    is_featured = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Featured articles appear in the hero section on the news page.",
    )
    published_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="Article won't appear until this date/time.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Managers
    objects = models.Manager()
    published = ArticlePublishedManager()

    class Meta:
        ordering = ["-published_at"]
        verbose_name = "News Article"
        verbose_name_plural = "News Articles"
        indexes = [
            models.Index(fields=["-published_at", "is_published"]),
            models.Index(fields=["is_featured", "-published_at"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:255]
            # Handle duplicate slugs
            if NewsArticle.objects.filter(slug=self.slug).exists():
                self.slug = f"{self.slug}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        if not self.excerpt and self.body:
            clean_text = strip_tags(self.body)
            self.excerpt = (
                clean_text[:297] + "..." if len(clean_text) > 300 else clean_text
            )
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("news:article_detail", kwargs={"slug": self.slug})

    @property
    def has_image(self):
        return bool(self.featured_image_id)


class Newsletter(models.Model):
    """Archived newsletter PDFs (digitized historical issues)."""

    # Core fields
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(
        blank=True,
        help_text="Optional description or summary of this issue.",
    )

    # Issue identification
    issue_date = models.DateField(
        help_text="Publication date of this newsletter issue.",
        db_index=True,
    )
    volume = models.PositiveSmallIntegerField(null=True, blank=True)
    issue_number = models.PositiveSmallIntegerField(null=True, blank=True)

    # Files
    pdf_file = FilerFileField(
        on_delete=models.PROTECT,
        related_name="newsletter_pdfs",
        help_text="The newsletter PDF file.",
    )
    cover_image = FilerImageField(
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="newsletter_covers",
        help_text="Cover image or thumbnail for display.",
    )

    # Metadata
    is_published = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Managers
    objects = models.Manager()
    published = NewsletterPublishedManager()

    class Meta:
        ordering = ["-issue_date"]
        verbose_name = "Newsletter"
        verbose_name_plural = "Newsletters"
        indexes = [
            models.Index(fields=["-issue_date", "is_published"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["volume", "issue_number"],
                name="unique_volume_issue",
                condition=models.Q(volume__isnull=False, issue_number__isnull=False),
            )
        ]

    def __str__(self):
        if self.volume and self.issue_number:
            return f"{self.title} (Vol. {self.volume}, No. {self.issue_number})"
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            date_str = self.issue_date.strftime("%Y-%m")
            base_slug = f"{date_str}-{slugify(self.title)[:200]}"
            self.slug = base_slug
            # Handle duplicate slugs
            if Newsletter.objects.filter(slug=self.slug).exists():
                self.slug = f"{base_slug}-{self.pk or 'new'}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("news:newsletter_detail", kwargs={"slug": self.slug})

    @property
    def issue_label(self):
        """Returns 'Vol. 5, No. 3' or empty string."""
        if self.volume and self.issue_number:
            return f"Vol. {self.volume}, No. {self.issue_number}"
        return ""

    @property
    def has_cover(self):
        return bool(self.cover_image_id)
