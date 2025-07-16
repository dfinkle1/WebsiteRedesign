from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def is_htmx(context):
    request = context.get("request")
    if not request:
        return False
    return request.headers.get("HX-Request") == "true"
