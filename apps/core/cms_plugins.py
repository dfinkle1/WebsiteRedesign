from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from django.utils.translation import gettext as _
from .models import StaffMember


@plugin_pool.register_plugin
class StaffMemberPlugin(CMSPluginBase):
    # model = StaffMember
    name = "Staff Member"
    module = _("Staff Members Plugin")
    render_template = "staff_member_plugin.html"
    cache = False

    def render(self, context, instance, placeholder):
        staff_members = StaffMember.objects.filter(is_visible=True).order_by("order")
        context.update({"staff_members": staff_members})
        return context
