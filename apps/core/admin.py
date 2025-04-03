from django.contrib import admin
from adminsortable2.admin import SortableAdminMixin
from .models import StaffMember, NewsArticle


class StaffMemberAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "is_visible", "order")


class NewsArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "text", "news_image", "featured", "published_date")


admin.site.register(StaffMember, StaffMemberAdmin)
admin.site.register(NewsArticle, NewsArticleAdmin)
