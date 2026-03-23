from django import template
from django.utils import timezone

from ..models import Program

register = template.Library()


@register.inclusion_tag("workshop_list.html")
def show_workshops(limit=None):

    workshops = Program.objects.filter(type=Program.ProgramType.WORKSHOP)
    if limit:
        workshops = workshops[:limit]
    return {"workshops": workshops}


@register.inclusion_tag("programs/partials/communities_tabs.html")
def show_communities():
    from django.db.models import Q
    today = timezone.localdate()
    current = Program.objects.filter(
        type=Program.ProgramType.COMMUNITY,
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=today)
    ).order_by("title")

    past = Program.objects.filter(
        type=Program.ProgramType.COMMUNITY,
        end_date__lt=today,
    ).order_by("-end_date")

    return {"current_communities": current, "past_communities": past}
