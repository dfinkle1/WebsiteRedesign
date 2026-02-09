from django import template

from apps.preprints.models import Preprint

register = template.Library()


@register.inclusion_tag("preprints/preprint_list_partial.html", takes_context=True)
def show_preprints(context, year=None):
    """
    Display preprints filtered by year (from URL param or argument).

    Usage:
        {% load preprint_tags %}
        {% show_preprints %}  {# Uses ?year= from URL, defaults to most recent #}
        {% show_preprints year=2026 %}  {# Force specific year #}
    """
    request = context.get("request")

    years = list(
        Preprint.objects.values_list("year", flat=True)
        .distinct()
        .order_by("-year")
    )

    if not years:
        return {"preprints": [], "years": [], "selected_year": None}

    # Get year from URL param if not explicitly provided
    if year is None and request:
        year_param = request.GET.get("year")
        if year_param and year_param.isdigit():
            year = int(year_param)

    # Default to most recent year if not specified
    if year is None:
        year = years[0] if years else None

    preprints = Preprint.objects.by_year(year) if year else []

    return {
        "preprints": preprints,
        "years": years,
        "selected_year": year,
    }
