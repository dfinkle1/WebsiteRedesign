from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from djangocms_text.widgets import TextEditorWidget
from .models import NewsArticle, Newsletter, ArticleImage


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
