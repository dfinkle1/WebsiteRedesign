"""
Utility functions and mixins for the site.
"""
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import Http404


# Maximum page number allowed for pagination (prevents bot abuse)
MAX_PAGE_NUMBER = 100


def get_safe_page(request, paginator, max_page=MAX_PAGE_NUMBER):
    """
    Get a page from the paginator with safety caps.

    - Caps page number at max_page to prevent bot abuse
    - Returns first page for invalid input
    - Returns last valid page if requested page > actual pages

    Args:
        request: Django request object
        paginator: Django Paginator instance
        max_page: Maximum allowed page number (default: 100)

    Returns:
        Page object

    Raises:
        Http404: If requested page exceeds max_page limit
    """
    page = request.GET.get("page", 1)

    # Validate page number
    try:
        page_num = int(page)
    except (ValueError, TypeError):
        page_num = 1

    # Cap at maximum allowed page
    if page_num > max_page:
        raise Http404(f"Page {page_num} does not exist.")

    # Also cap at actual number of pages
    if page_num > paginator.num_pages and paginator.num_pages > 0:
        page_num = paginator.num_pages

    try:
        return paginator.page(page_num)
    except PageNotAnInteger:
        return paginator.page(1)
    except EmptyPage:
        return paginator.page(paginator.num_pages) if paginator.num_pages > 0 else paginator.page(1)


class SafePaginationMixin:
    """
    Mixin for class-based views that caps pagination to prevent bot abuse.

    Usage:
        class MyListView(SafePaginationMixin, ListView):
            model = MyModel
            paginate_by = 10
            max_page = 50  # Optional, defaults to MAX_PAGE_NUMBER
    """
    max_page = MAX_PAGE_NUMBER

    def paginate_queryset(self, queryset, page_size):
        """Override to add page cap."""
        paginator = self.get_paginator(
            queryset, page_size, orphans=self.get_paginate_orphans(),
            allow_empty_first_page=self.get_allow_empty()
        )

        page_kwarg = self.page_kwarg
        page = self.kwargs.get(page_kwarg) or self.request.GET.get(page_kwarg) or 1

        try:
            page_number = int(page)
        except (ValueError, TypeError):
            page_number = 1

        # Enforce max page cap
        if page_number > self.max_page:
            raise Http404(f"Page {page_number} does not exist.")

        # Call parent implementation
        return super().paginate_queryset(queryset, page_size)
