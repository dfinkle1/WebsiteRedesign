"""
Preprint Series Models

Tracks papers and preprints that resulted from AIM programs.
"""

from django.db import models


class PreprintManager(models.Manager):
    """Custom manager with common queries."""

    def published(self):
        """Return all preprints ordered by year desc, sequence desc."""
        return self.get_queryset().order_by("-year", "-sequence")

    def by_year(self, year):
        """Get preprints for a specific year/volume."""
        return self.published().filter(year=year)


class Preprint(models.Model):
    """
    A paper or preprint from the AIM preprint series.

    These are papers that acknowledge AIM support, typically arising
    from workshops, SQuaREs, or other AIM programs.
    """

    class ProgramType(models.TextChoices):
        WORKSHOP = "workshop", "Workshop"
        SQUARE = "square", "SQuaRE"
        ARC = "arc", "ARC"
        REUF = "reuf", "REUF"
        OTHER = "other", "Other"

    # Display fields
    year = models.PositiveIntegerField(
        help_text="Volume year (e.g., 2026)"
    )
    sequence = models.PositiveIntegerField(
        help_text="Entry number within the year (e.g., 5 for 2026-5)"
    )
    title = models.CharField(max_length=500)
    authors = models.TextField(
        help_text="Comma-separated author names"
    )

    # Link fields (one or the other)
    arxiv_id = models.CharField(
        max_length=30,
        blank=True,
        help_text="ArXiv ID (e.g., 2601.11912 or math.AG/0601001). Leave blank if using custom URL."
    )
    url = models.URLField(
        blank=True,
        help_text="Custom URL if not on arXiv"
    )

    # Metadata (logged but not displayed)
    program_type = models.CharField(
        max_length=20,
        choices=ProgramType.choices,
        blank=True,
    )
    program_code = models.CharField(
        max_length=20,
        blank=True,
        help_text="Program code (e.g., 1269)"
    )
    aim_thanks_page = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Page number in AIM thanks"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PreprintManager()

    class Meta:
        ordering = ["-year", "-sequence"]
        unique_together = ["year", "sequence"]
        verbose_name = "Preprint"
        verbose_name_plural = "Preprints"
        indexes = [
            models.Index(fields=["-year", "-sequence"]),
        ]

    def __str__(self):
        return f"{self.entry_id}: {self.title[:50]}"

    @property
    def entry_id(self):
        """Return formatted entry ID like '2026-5'."""
        return f"{self.year}-{self.sequence}"

    @property
    def paper_url(self):
        """Return the URL to the paper (arXiv or custom)."""
        if self.arxiv_id:
            arxiv_id = self.arxiv_id
            # Old format like "math.NT/0609210" -> "math/0609210"
            # But "math-ph/0512023" stays as-is
            if "/" in arxiv_id and "." in arxiv_id.split("/")[0]:
                # Has format like "subject.class/number", strip the .class
                parts = arxiv_id.split("/")
                subject = parts[0].split(".")[0]  # "math.NT" -> "math"
                arxiv_id = f"{subject}/{parts[1]}"
            return f"https://arxiv.org/abs/{arxiv_id}"
        return self.url or ""

    @property
    def authors_list(self):
        """Return authors as a list."""
        return [a.strip() for a in self.authors.split(",") if a.strip()]
