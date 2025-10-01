from django.contrib import admin
from django.urls import include, path
from django.conf.urls.i18n import i18n_patterns
from django.conf import settings
from django.conf.urls.static import static
import debug_toolbar

urlpatterns = i18n_patterns(
    path("admin/", admin.site.urls),
    # ✅ Your custom app takes root first
    path("", include("apps.core.urls")),
    path("events/", include("apps.events.urls")),
    # ✅ CMS handles everything else
    path("", include("cms.urls")),
    path("news/", include("apps.news.urls")),
    path("", include("apps.reimbursements.urls")),
)

if settings.DEBUG:
    urlpatterns.insert(0, path("__debug__/", include(debug_toolbar.urls)))
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
