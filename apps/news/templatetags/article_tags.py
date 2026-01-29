from django import template
from apps.news.models import NewsArticle
from apps.news.views import get_featured_article, get_recent_articles

register = template.Library()


@register.inclusion_tag("list.html")
def render_news_list():
    list = NewsArticle.objects.all()
    return {"list": list}


@register.inclusion_tag("featured_article.html")
def render_featured_article():
    """Render the featured article hero section."""
    return {"article": get_featured_article()}


@register.inclusion_tag("news_carousel.html")
def render_news_carousel(limit=5):
    return {"articles": get_recent_articles(limit=limit, exclude_featured=True)}
