from django import template
from apps.news.models import NewsArticle

register = template.Library()


@register.inclusion_tag("list.html")
def render_news_list():
    list = NewsArticle.objects.all()
    return {"list": list}


@register.inclusion_tag("featured_article.html")
def render_featured_article():
    article = (
        NewsArticle.objects.filter(featured=True).order_by("-published_date").first()
    )
    return {"article": article}


@register.inclusion_tag("news_carousel.html")
def render_news_carousel():
    articles = NewsArticle.objects.filter(featured=False).order_by("-published_date")[
        :5
    ]
    return {"articles": articles}
