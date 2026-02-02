"""
Core views for the site (robots.txt, error pages, etc.)
"""
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_GET


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
