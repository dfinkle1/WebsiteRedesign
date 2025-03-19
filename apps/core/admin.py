from django.contrib import admin

from .models import StaffMember, NewsArticle

admin.site.register(StaffMember)
admin.site.register(NewsArticle)
