"""
Core views for the site (robots.txt, error pages, etc.)
"""
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_GET


# ---------------------------------------------------------------------------
# Error handlers — registered in urls.py as handler404/403/500
# ---------------------------------------------------------------------------

def view_404(request, exception=None):
    return render(request, "404.html", {}, status=404)


def view_403(request, exception=None):
    return render(request, "403.html", {}, status=403)


def view_500(request):
    return render(request, "500.html", {}, status=500)


# ---------------------------------------------------------------------------
# Health check — for monitoring/load balancer use
# ---------------------------------------------------------------------------

def health_check(request):
    from django.db import connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"status": "ok", "db": "connected"})
    except Exception as e:
        return JsonResponse({"status": "error", "db": str(e)}, status=503)


@require_GET
@cache_page(60 * 60 * 24)  # Cache for 24 hours
def robots_txt(request):
    """
    Serve robots.txt to guide search engine crawlers.

    - Allows indexing of main content
    - Blocks admin, accounts, and other sensitive areas
    - Rate limits crawlers with Crawl-delay
    """
    lines = [
        "User-agent: *",
        "",
        "# Allow main content",
        "Allow: /",
        "",
        "# Disallow admin and sensitive areas",
        "Disallow: /admin/",
        "Disallow: /accounts/",
        "Disallow: /enrollments/",
        "Disallow: /reimbursements/",
        "",
        "# Disallow query parameters that generate duplicate content",
        "Disallow: /*?page=",
        "Disallow: /*?search=",
        "Disallow: /*?year=",
        "",
        "# Rate limit crawling (seconds between requests)",
        "Crawl-delay: 2",
        "",
        "# Sitemap (if available)",
        f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")
