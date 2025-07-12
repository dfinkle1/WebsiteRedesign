from django import template
from apps.staff.models import StaffMember

register = template.Library()


@register.inclusion_tag("staff_list.html")
def render_staff():
    staff = StaffMember.objects.filter(is_visible=True).order_by("order")
    return {"staff": staff}
