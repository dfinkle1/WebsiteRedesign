from django.urls import path
from . import views

urlpatterns = [
    path("news/story/<slug:slug>", views.news_detail, name="news-article-detail"),
]
