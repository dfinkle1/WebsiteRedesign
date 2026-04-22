from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from programs.views import home, home2
from mysite.views import robots_txt, view_404, view_403, view_500, health_check
import debug_toolbar

# Custom error handlers
handler404 = "mysite.views.view_404"
handler403 = "mysite.views.view_403"
handler500 = "mysite.views.view_500"

# All URLs (no language prefix)
urlpatterns = [
    path("robots.txt", robots_txt, name="robots_txt"),
    path("health/", health_check, name="health_check"),
    path("admin/", admin.site.urls),
    # Custom accounts URLs first (takes precedence over allauth)
    path("accounts/", include("accounts.urls", "accounts")),
    # Allauth URLs for OAuth callbacks only
    path("accounts/", include("allauth.urls")),
    path("", include("programs.urls")),
    path("events/", include("apps.events.urls")),
    path("news/", include("apps.news.urls")),
    path("reimbursements/", include("apps.reimbursements.urls")),
    path("enrollments/", include("enrollments.urls")),
    path("checklists/", include("apps.checklists.urls")),
    path("timeeffort/", include("apps.timeeffort.urls")),
    path("", include("apps.donations.urls")),
    path("home2/", home2, name="home2"),
    path("", home, name="index"),
    # CMS handles everything else - must be last
    path("", include("cms.urls")),
]

if settings.DEBUG:
    urlpatterns.insert(0, path("__debug__/", include(debug_toolbar.urls)))
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
