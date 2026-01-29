from django.urls import path
from . import views

app_name = "news"

urlpatterns = [
    # News Articles
    path("", views.ArticleListView.as_view(), name="article_list"),
    path(
        "article/<slug:slug>/",
        views.ArticleDetailView.as_view(),
        name="article_detail",
    ),
    path("archive/", views.ArticleArchiveView.as_view(), name="article_archive"),
    path(
        "archive/<int:year>/",
        views.ArticleYearView.as_view(),
        name="article_year",
    ),
    # Newsletters
    path("newsletters/", views.NewsletterListView.as_view(), name="newsletter_list"),
    path(
        "newsletter/<slug:slug>/",
        views.NewsletterDetailView.as_view(),
        name="newsletter_detail",
    ),
    path(
        "newsletters/<int:year>/",
        views.NewsletterYearView.as_view(),
        name="newsletter_year",
    ),
]
