# templatetags/program_cards.py
from django import template
from programs.services import get_upcoming_workshops

register = template.Library()


@register.inclusion_tag("partials/program_cards.html")
def render_program_cards(limit=10):
    return {"workshops": get_upcoming_workshops(limit=limit)}
