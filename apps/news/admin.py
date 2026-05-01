from django.contrib import admin
from django.db import models
from django.utils.html import format_html, mark_safe
from django.contrib import messages
from djangocms_text.widgets import TextEditorWidget
from django.db.models import F
from .models import NewsArticle, Newsletter, ArticleImage, HomepageFeedItem


class ArticleImageInline(admin.TabularInline):
    """Inline for adding multiple images to an article."""

    model = ArticleImage
    extra = 1
    fields = ["image", "caption", "order", "image_preview"]
    readonly_fields = ["image_preview"]
    ordering = ["order", "id"]

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="100" height="75" '
                'style="object-fit: cover; border-radius: 4px;" />',
                obj.image.url,
            )
        return "-"

    image_preview.short_description = "Preview"


@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "published_at",
        "is_published",
        "is_featured",
        "image_preview",
        "gallery_count",
    ]
    list_filter = ["is_published", "is_featured", "published_at"]
    search_fields = ["title", "excerpt", "body"]
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "published_at"
    ordering = ["-published_at"]
    list_editable = ["is_published", "is_featured"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [ArticleImageInline]

    fieldsets = (
        (
            None,
            {
                "fields": ("title", "slug", "body", "excerpt"),
            },
        ),
        (
            "Media",
            {
                "fields": ("featured_image",),
            },
        ),
        (
            "Publishing",
            {
                "fields": ("is_published", "is_featured", "published_at"),
            },
        ),
        (
            "Metadata",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    formfield_overrides = {
        models.TextField: {"widget": TextEditorWidget},
    }

    def image_preview(self, obj):
        if obj.featured_image:
            return format_html(
                '<img src="{}" width="50" height="50" '
                'style="object-fit: cover; border-radius: 4px;" />',
                obj.featured_image.url,
            )
        return "-"

    image_preview.short_description = "Image"

    def gallery_count(self, obj):
        count = obj.images.count()
        if count:
            return f"{count} image{'s' if count > 1 else ''}"
        return "-"

    gallery_count.short_description = "Gallery"

    def response_change(self, request, obj):
        """Add a 'View live' link after saving."""
        response = super().response_change(request, obj)
        if obj.is_published:
            view_url = obj.get_absolute_url()
            messages.info(
                request,
                format_html(
                    '📄 <a href="{}" target="_blank" style="color: #fff; text-decoration: underline;">View live article</a>',
                    view_url,
                ),
            )
        return response

    def response_add(self, request, obj, post_url_continue=None):
        """Add a 'View live' link after creating a new article."""
        response = super().response_add(request, obj, post_url_continue)
        if obj.is_published:
            view_url = obj.get_absolute_url()
            messages.info(
                request,
                format_html(
                    '📄 <a href="{}" target="_blank" style="color: #fff; text-decoration: underline;">View live article</a>',
                    view_url,
                ),
            )
        return response


@admin.register(HomepageFeedItem)
class HomepageFeedItemAdmin(admin.ModelAdmin):
    list_display = ["display_title", "source_badge", "item_type", "published_at", "pin_order", "is_active"]
    list_filter = ["item_type", "is_active"]
    list_editable = ["is_active", "pin_order"]
    search_fields = ["title", "excerpt", "article__title"]
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["article"]

    fieldsets = (
        (
            "Linked Article (optional)",
            {
                "fields": ("article",),
                "description": (
                    "Link to an existing news article to use its content as the base. "
                    "When linked, any field below that is left blank will automatically "
                    "inherit the article's value (title, excerpt, image, URL). "
                    "Leave this blank for standalone announcements or custom entries."
                ),
            },
        ),
        (
            "Content",
            {
                "fields": ("title", "item_type", "excerpt", "body", "url", "image"),
                "description": (
                    "If a linked article is set above, you can leave any of these blank "
                    "and the article's own value will be used."
                ),
            },
        ),
        (
            "Publishing",
            {
                "fields": ("is_active", "published_at", "pin_order"),
                "description": (
                    "Pinned items appear first regardless of date. "
                    "Leave Pin Order blank to sort chronologically."
                ),
            },
        ),
        (
            "Metadata",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    formfield_overrides = {
        models.TextField: {"widget": TextEditorWidget},
    }

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .select_related("article")
            .order_by(F("pin_order").asc(nulls_last=True), "-published_at")
        )

    def display_title(self, obj):
        if obj.title:
            return obj.title
        if obj.article_id:
            return f"→ {obj.article.title}"
        return "(untitled)"

    display_title.short_description = "Title"

    def source_badge(self, obj):
        if obj.article_id:
            return mark_safe('<span style="color:#1f6b47;font-size:0.72rem;font-weight:700;">ARTICLE</span>')
        return mark_safe('<span style="color:#6c757d;font-size:0.72rem;">MANUAL</span>')

    source_badge.short_description = "Source"


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "issue_date",
        "volume_issue",
        "is_published",
        "cover_preview",
    ]
    list_filter = ["is_published", "issue_date"]
    search_fields = ["title", "description"]
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "issue_date"
    ordering = ["-issue_date"]
    list_editable = ["is_published"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            None,
            {
                "fields": ("title", "slug", "description"),
            },
        ),
        (
            "Issue Details",
            {
                "fields": ("issue_date", "volume", "issue_number"),
            },
        ),
        (
            "Files",
            {
                "fields": ("pdf_file", "cover_image"),
            },
        ),
        (
            "Publishing",
            {
                "fields": ("is_published",),
            },
        ),
        (
            "Metadata",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def volume_issue(self, obj):
        return obj.issue_label or "-"

    volume_issue.short_description = "Vol/Issue"

    def cover_preview(self, obj):
        if obj.cover_image:
            return format_html(
                '<img src="{}" width="40" height="50" '
                'style="object-fit: cover; border-radius: 2px;" />',
                obj.cover_image.url,
            )
        return "-"

    cover_preview.short_description = "Cover"
