from django import template
from ..models import Program

register = template.Library()


@register.inclusion_tag("workshop_list.html")
def show_workshops(limit=None):

    workshops = Program.objects.filter(type=Program.ProgramType.WORKSHOP)
    if limit:
        workshops = workshops[:limit]
    return {"workshops": workshops}
