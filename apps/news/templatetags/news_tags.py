"""
News template tags for use in templates outside the news app (e.g., homepage).

Usage:
    {% load news_tags %}
    {% featured_article %}
    {% news_carousel %}
    {% news_carousel limit=3 %}
    {% recent_newsletters %}
    {% recent_newsletters limit=4 %}
"""

from django import template
from apps.news.views import get_featured_article, get_recent_articles, get_recent_newsletters

register = template.Library()


@register.inclusion_tag("news/includes/_article_hero.html")
def featured_article():
    """Render the featured article hero section."""
    return {"article": get_featured_article()}


@register.inclusion_tag("news/includes/_news_carousel.html")
def news_carousel(limit=5):
    """Render a carousel/grid of recent articles (excludes featured)."""
    return {"articles": get_recent_articles(limit=limit, exclude_featured=True)}


@register.inclusion_tag("news/includes/_newsletter_grid.html")
def recent_newsletters(limit=6):
    """Render a grid of recent newsletters."""
    return {"newsletters": get_recent_newsletters(limit=limit)}


# Backwards compatibility aliases for existing templates
@register.inclusion_tag("news/includes/_article_hero.html")
def render_featured_article():
    """Backwards compatible alias for featured_article."""
    return {"article": get_featured_article()}


@register.inclusion_tag("news/includes/_news_carousel.html")
def render_news_carousel():
    """Backwards compatible alias for news_carousel."""
    return {"articles": get_recent_articles(limit=5, exclude_featured=True)}


@register.inclusion_tag("news/includes/_newsletter_grid.html")
def render_newsletters():
    """Backwards compatible alias for recent_newsletters."""
    return {"newsletters": get_recent_newsletters(limit=12)}


@register.inclusion_tag("news/includes/_news_carousel.html")
def render_news_list():
    """Backwards compatible alias - renders all published articles as a grid."""
    return {"articles": get_recent_articles(limit=50, exclude_featured=False)}
