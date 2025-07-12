from django.shortcuts import render, get_object_or_404
from .models import *


def news_detail(request, slug):
    article = get_object_or_404(NewsArticle, slug=slug)
    return render(request, "article_detail.html", {"article": article})


def news_view(request):
    news_articles = NewsArticle.objects.all()
    context = {"news_articles": news_articles}
    return render(request, "news.html", context)
