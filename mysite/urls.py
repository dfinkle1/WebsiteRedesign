from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
import debug_toolbar


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),  # Your existing app's URLs
    path("", include("cms.urls")),  # Include Django CMS URLs
    path("news/", include("apps.news.urls")),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    import debug_toolbar

    urlpatterns.insert(0, path("__debug__/", include(debug_toolbar.urls)))
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
