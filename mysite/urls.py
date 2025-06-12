from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path
from django.shortcuts import redirect
from django.views.i18n import JavaScriptCatalog
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),  # Your existing app's URLs
    path("", include("cms.urls")),  # Include Django CMS URLs
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    urlpatterns += tuple(static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT))
    urlpatterns += tuple(
        static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    )
