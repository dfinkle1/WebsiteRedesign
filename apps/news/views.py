from django.views.generic import ListView, DetailView
from django.db.models.functions import ExtractYear
from .models import NewsArticle, Newsletter


class ArticleListView(ListView):
    """Paginated list of published news articles."""

    model = NewsArticle
    template_name = "news/article_list.html"
    context_object_name = "articles"
    paginate_by = 12

    def get_queryset(self):
        return NewsArticle.published.select_related("featured_image").only(
            "title",
            "slug",
            "excerpt",
            "published_at",
            "is_featured",
            "featured_image",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["featured_article"] = (
            NewsArticle.published.filter(is_featured=True)
            .select_related("featured_image")
            .first()
        )
        return context


class ArticleDetailView(DetailView):
    """Single article page."""

    model = NewsArticle
    template_name = "news/article_detail.html"
    context_object_name = "article"

    def get_queryset(self):
        # Allow preview of unpublished for staff
        if self.request.user.is_staff:
            return NewsArticle.objects.select_related("featured_image")
        return NewsArticle.published.select_related("featured_image")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["related_articles"] = (
            NewsArticle.published.exclude(pk=self.object.pk)
            .select_related("featured_image")
            .only("title", "slug", "excerpt", "published_at", "featured_image")[:3]
        )
        return context


class ArticleArchiveView(ListView):
    """Archive index showing available years."""

    model = NewsArticle
    template_name = "news/article_archive.html"
    context_object_name = "years"

    def get_queryset(self):
        return (
            NewsArticle.published.annotate(year=ExtractYear("published_at"))
            .values("year")
            .distinct()
            .order_by("-year")
        )


class ArticleYearView(ListView):
    """Articles from a specific year."""

    model = NewsArticle
    template_name = "news/article_list.html"
    context_object_name = "articles"
    paginate_by = 20

    def get_queryset(self):
        return NewsArticle.published.filter(
            published_at__year=self.kwargs["year"]
        ).select_related("featured_image")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["year"] = self.kwargs["year"]
        context["is_archive"] = True
        return context


class NewsletterListView(ListView):
    """Paginated list of newsletters."""

    model = Newsletter
    template_name = "news/newsletter_list.html"
    context_object_name = "newsletters"
    paginate_by = 12

    def get_queryset(self):
        return Newsletter.published.select_related("cover_image", "pdf_file")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get available years for filtering
        context["available_years"] = (
            Newsletter.published.annotate(year=ExtractYear("issue_date"))
            .values_list("year", flat=True)
            .distinct()
            .order_by("-year")
        )
        return context


class NewsletterDetailView(DetailView):
    """Newsletter detail page with PDF embed or download link."""

    model = Newsletter
    template_name = "news/newsletter_detail.html"
    context_object_name = "newsletter"

    def get_queryset(self):
        if self.request.user.is_staff:
            return Newsletter.objects.select_related("cover_image", "pdf_file")
        return Newsletter.published.select_related("cover_image", "pdf_file")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Adjacent newsletters for navigation
        context["previous_newsletter"] = (
            Newsletter.published.filter(issue_date__lt=self.object.issue_date)
            .order_by("-issue_date")
            .first()
        )
        context["next_newsletter"] = (
            Newsletter.published.filter(issue_date__gt=self.object.issue_date)
            .order_by("issue_date")
            .first()
        )
        return context


class NewsletterYearView(ListView):
    """Newsletters from a specific year."""

    model = Newsletter
    template_name = "news/newsletter_list.html"
    context_object_name = "newsletters"
    paginate_by = 20

    def get_queryset(self):
        return Newsletter.published.filter(
            issue_date__year=self.kwargs["year"]
        ).select_related("cover_image", "pdf_file")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["year"] = self.kwargs["year"]
        context["is_archive"] = True
        # Get available years for filtering
        context["available_years"] = (
            Newsletter.published.annotate(year=ExtractYear("issue_date"))
            .values_list("year", flat=True)
            .distinct()
            .order_by("-year")
        )
        return context


# ==============================================
# HELPER FUNCTIONS FOR TEMPLATE TAGS
# ==============================================


def get_featured_article():
    """Used by homepage template tag."""
    return (
        NewsArticle.published.filter(is_featured=True)
        .select_related("featured_image")
        .first()
    )


def get_recent_articles(limit=5, exclude_featured=True):
    """Used by homepage carousel template tag."""
    qs = NewsArticle.published.select_related("featured_image")
    if exclude_featured:
        qs = qs.filter(is_featured=False)
    return qs[:limit]


def get_recent_newsletters(limit=6):
    """Used by homepage template tag if needed."""
    return Newsletter.published.select_related("cover_image")[:limit]
