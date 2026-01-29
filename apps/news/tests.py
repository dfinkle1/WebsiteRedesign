from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import NewsArticle, Newsletter

User = get_user_model()


class NewsArticleModelTest(TestCase):
    """Tests for the NewsArticle model."""

    def test_slug_auto_generated(self):
        """Slug should be auto-generated from title."""
        article = NewsArticle.objects.create(
            title="Test Article Title",
            body="Some content here",
            published_at=timezone.now(),
            is_published=True,
        )
        self.assertEqual(article.slug, "test-article-title")

    def test_slug_handles_duplicates(self):
        """Duplicate slugs should get a timestamp suffix."""
        NewsArticle.objects.create(
            title="Test Article",
            slug="test-article",
            body="First article",
            published_at=timezone.now(),
            is_published=True,
        )
        article2 = NewsArticle.objects.create(
            title="Test Article",
            body="Second article",
            published_at=timezone.now(),
            is_published=True,
        )
        self.assertNotEqual(article2.slug, "test-article")
        self.assertTrue(article2.slug.startswith("test-article-"))

    def test_excerpt_auto_generated(self):
        """Excerpt should be auto-generated from body if not provided."""
        article = NewsArticle.objects.create(
            title="Test",
            body="<p>This is <strong>HTML</strong> content that should be stripped.</p>",
            published_at=timezone.now(),
            is_published=True,
        )
        self.assertIn("This is HTML content", article.excerpt)
        self.assertNotIn("<p>", article.excerpt)
        self.assertNotIn("<strong>", article.excerpt)

    def test_excerpt_not_overwritten(self):
        """Manually set excerpt should not be overwritten."""
        article = NewsArticle.objects.create(
            title="Test",
            body="Long body content here",
            excerpt="Custom excerpt",
            published_at=timezone.now(),
            is_published=True,
        )
        self.assertEqual(article.excerpt, "Custom excerpt")

    def test_published_manager(self):
        """Published manager should only return published articles."""
        # Published article
        NewsArticle.objects.create(
            title="Published",
            slug="published",
            body="x",
            is_published=True,
            published_at=timezone.now(),
        )
        # Draft article
        NewsArticle.objects.create(
            title="Draft",
            slug="draft",
            body="x",
            is_published=False,
            published_at=timezone.now(),
        )
        # Future article
        NewsArticle.objects.create(
            title="Future",
            slug="future",
            body="x",
            is_published=True,
            published_at=timezone.now() + timedelta(days=7),
        )

        self.assertEqual(NewsArticle.objects.count(), 3)
        self.assertEqual(NewsArticle.published.count(), 1)

    def test_get_absolute_url(self):
        """get_absolute_url should return the correct URL."""
        article = NewsArticle.objects.create(
            title="Test Article",
            slug="test-article",
            body="Content",
            published_at=timezone.now(),
            is_published=True,
        )
        self.assertEqual(
            article.get_absolute_url(), reverse("news:article_detail", args=["test-article"])
        )

    def test_str_method(self):
        """__str__ should return the title."""
        article = NewsArticle(title="My Article Title")
        self.assertEqual(str(article), "My Article Title")


class NewsletterModelTest(TestCase):
    """Tests for the Newsletter model."""

    def test_issue_label_with_volume_and_number(self):
        """issue_label should return formatted string when both are set."""
        newsletter = Newsletter(volume=5, issue_number=3)
        self.assertEqual(newsletter.issue_label, "Vol. 5, No. 3")

    def test_issue_label_without_volume(self):
        """issue_label should return empty string when volume is missing."""
        newsletter = Newsletter(issue_number=3)
        self.assertEqual(newsletter.issue_label, "")

    def test_str_with_volume_issue(self):
        """__str__ should include volume/issue when present."""
        newsletter = Newsletter(title="Spring Newsletter", volume=5, issue_number=3)
        self.assertEqual(str(newsletter), "Spring Newsletter (Vol. 5, No. 3)")

    def test_str_without_volume_issue(self):
        """__str__ should return just title when no volume/issue."""
        newsletter = Newsletter(title="Spring Newsletter")
        self.assertEqual(str(newsletter), "Spring Newsletter")


class ArticleViewTest(TestCase):
    """Tests for article views."""

    def setUp(self):
        self.client = Client()
        self.article = NewsArticle.objects.create(
            title="Test Article",
            slug="test-article",
            body="<p>Article content here.</p>",
            is_published=True,
            published_at=timezone.now(),
        )

    def test_article_list_view(self):
        """Article list view should render successfully."""
        response = self.client.get(reverse("news:article_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Article")
        self.assertTemplateUsed(response, "news/article_list.html")

    def test_article_detail_view(self):
        """Article detail view should render successfully."""
        response = self.client.get(
            reverse("news:article_detail", kwargs={"slug": "test-article"})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Article")
        self.assertTemplateUsed(response, "news/article_detail.html")

    def test_unpublished_article_404(self):
        """Unpublished articles should return 404 for anonymous users."""
        self.article.is_published = False
        self.article.save()
        response = self.client.get(
            reverse("news:article_detail", kwargs={"slug": "test-article"})
        )
        self.assertEqual(response.status_code, 404)

    def test_unpublished_article_visible_to_staff(self):
        """Staff users should be able to preview unpublished articles."""
        self.article.is_published = False
        self.article.save()

        staff_user = User.objects.create_user(
            username="staff", password="password", is_staff=True
        )
        self.client.login(username="staff", password="password")

        response = self.client.get(
            reverse("news:article_detail", kwargs={"slug": "test-article"})
        )
        self.assertEqual(response.status_code, 200)

    def test_article_archive_view(self):
        """Archive view should list available years."""
        response = self.client.get(reverse("news:article_archive"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "news/article_archive.html")

    def test_article_year_view(self):
        """Year archive view should filter by year."""
        year = self.article.published_at.year
        response = self.client.get(reverse("news:article_year", kwargs={"year": year}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Article")

    def test_featured_article_in_context(self):
        """Featured article should be in list view context."""
        self.article.is_featured = True
        self.article.save()

        response = self.client.get(reverse("news:article_list"))
        self.assertEqual(response.context["featured_article"], self.article)


class NewsletterViewTest(TestCase):
    """Tests for newsletter views."""

    def setUp(self):
        self.client = Client()
        # Note: Newsletter requires a pdf_file (FilerFileField)
        # In a full test, you'd need to mock or create a filer file
        # For now, we test what we can without file upload

    def test_newsletter_list_view(self):
        """Newsletter list view should render successfully."""
        response = self.client.get(reverse("news:newsletter_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "news/newsletter_list.html")


class URLTest(TestCase):
    """Tests for URL patterns."""

    def test_url_names(self):
        """All URL names should resolve correctly."""
        # Article URLs
        self.assertEqual(reverse("news:article_list"), "/news/")
        self.assertEqual(
            reverse("news:article_detail", kwargs={"slug": "test"}),
            "/news/article/test/",
        )
        self.assertEqual(reverse("news:article_archive"), "/news/archive/")
        self.assertEqual(
            reverse("news:article_year", kwargs={"year": 2024}),
            "/news/archive/2024/",
        )

        # Newsletter URLs
        self.assertEqual(reverse("news:newsletter_list"), "/news/newsletters/")
        self.assertEqual(
            reverse("news:newsletter_detail", kwargs={"slug": "test"}),
            "/news/newsletter/test/",
        )
        self.assertEqual(
            reverse("news:newsletter_year", kwargs={"year": 2024}),
            "/news/newsletters/2024/",
        )
