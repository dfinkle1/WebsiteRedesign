from django.contrib import admin
from .models import Newsletter, NewsArticle
from djangocms_text.widgets import TextEditorWidget
from djangocms_text.contrib.text_ckeditor4 import ckeditor4
from django import forms


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = ("title", "pdf_file", "photo")


class NewsArticleAdmin(admin.ModelAdmin):
    # form = NewsArticleForm
    list_display = ("title", "slug")


admin.site.register(NewsArticle, NewsArticleAdmin)
