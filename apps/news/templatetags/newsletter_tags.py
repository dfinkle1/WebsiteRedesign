from django import template
from apps.news.models import Newsletter

register = template.Library()


@register.inclusion_tag("newsletter_list.html")
def render_newsletters():
    newsletters = Newsletter.objects.all()
    return {"newsletters": newsletters}
