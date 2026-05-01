from dataclasses import dataclass
from typing import Optional

from django import template
from django.db.models import F
from django.utils import timezone

from apps.news.models import HomepageFeedItem, NewsArticle
from apps.news.views import get_featured_article, get_recent_articles

register = template.Library()


@dataclass
class FeedEntry:
    """Unified representation of a homepage feed item, regardless of source."""

    title: str
    excerpt: str
    body: str
    image: object          # filer image instance or None
    item_type: str         # "news", "announcement", "event", "milestone"
    item_type_display: str # "News", "Announcement", etc.
    url: str
    published_at: object   # datetime
    pin_order: Optional[int]
    is_pinned: bool


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


@register.inclusion_tag("homepage_feed.html")
def render_homepage_feed(limit=5):
    """
    Render the homepage news column as a merged two-stream feed.

    Stream 1 — Manual HomepageFeedItem entries (active, published).
      These are explicit staff-created items: announcements, pinned news,
      custom events, milestones.  They may optionally link to a NewsArticle,
      in which case blank fields fall back to the article's values.

    Stream 2 — Auto-surfaced NewsArticles where is_featured=True.
      Articles whose PK is already referenced by a manual item are excluded
      so nothing appears twice.

    Sort order: pinned items first (by pin_order ascending), then all
    remaining items sorted by published_at descending.
    """
    now = timezone.now()

    # ── Stream 1: manual items ────────────────────────────────────────────
    manual_items = list(
        HomepageFeedItem.objects
        .filter(is_active=True, published_at__lte=now)
        .select_related("image", "article", "article__featured_image")
        .order_by(F("pin_order").asc(nulls_last=True), "-published_at")
    )

    # Article PKs already represented — exclude from auto-stream
    covered_article_pks = {item.article_id for item in manual_items if item.article_id}

    # ── Stream 2: auto-surfaced featured articles ─────────────────────────
    auto_articles = list(
        NewsArticle.objects
        .filter(is_featured=True, is_published=True, published_at__lte=now)
        .exclude(pk__in=covered_article_pks)
        .select_related("featured_image")
        .order_by("-published_at")
    )

    # ── Convert both streams to FeedEntry ────────────────────────────────
    entries: list[FeedEntry] = []

    for item in manual_items:
        art = item.article  # may be None
        entries.append(FeedEntry(
            title=item.title or (art.title if art else ""),
            excerpt=item.excerpt or (art.excerpt if art else ""),
            body=item.body,
            image=item.image or (art.featured_image if art else None),
            item_type=item.item_type,
            item_type_display=item.get_item_type_display(),
            url=item.url or (art.get_absolute_url() if art else ""),
            published_at=item.published_at,
            pin_order=item.pin_order,
            is_pinned=item.pin_order is not None,
        ))

    for article in auto_articles:
        entries.append(FeedEntry(
            title=article.title,
            excerpt=article.excerpt,
            body="",
            image=article.featured_image,
            item_type=HomepageFeedItem.ItemType.NEWS,
            item_type_display="News",
            url=article.get_absolute_url(),
            published_at=article.published_at,
            pin_order=None,
            is_pinned=False,
        ))

    # ── Merge and sort ────────────────────────────────────────────────────
    # Pinned items retain their query order (pin_order asc, already sorted).
    # Unpinned items from both streams are merged and sorted by date desc.
    pinned = [e for e in entries if e.is_pinned]
    unpinned = sorted(
        [e for e in entries if not e.is_pinned],
        key=lambda e: e.published_at,
        reverse=True,
    )

    return {"items": (pinned + unpinned)[:limit]}
