from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
import debug_toolbar

# All URLs (no language prefix)
urlpatterns = [
    path("admin/", admin.site.urls),
    # Custom accounts URLs first (takes precedence over allauth)
    path("accounts/", include("accounts.urls", "accounts")),
    # Allauth URLs for OAuth callbacks only
    path("accounts/", include("allauth.urls")),
    path("", include("programs.urls")),
    path("events/", include("apps.events.urls")),
    path("news/", include("apps.news.urls")),
    path("", include("apps.reimbursements.urls")),
    # CMS handles everything else - must be last
    path("", include("cms.urls")),
]

if settings.DEBUG:
    urlpatterns.insert(0, path("__debug__/", include(debug_toolbar.urls)))
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
