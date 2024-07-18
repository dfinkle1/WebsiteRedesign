from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),  # Your existing app's URLs
]

urlpatterns += i18n_patterns(
    path("", include("cms.urls")),  # Include Django CMS URLs
)
