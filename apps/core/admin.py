from django.contrib import admin
from adminsortable2.admin import SortableAdminMixin
from .models import StaffMember, NewsArticle


class StaffMemberAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "is_visible", "order")


admin.site.register(StaffMember, StaffMemberAdmin)
admin.site.register(NewsArticle)
