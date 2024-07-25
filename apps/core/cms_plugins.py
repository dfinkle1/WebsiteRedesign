from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from django.utils.translation import gettext as _
from .forms import StaffMemberForm
from .models import StaffMember


@plugin_pool.register_plugin
class StaffMemberPlugin(CMSPluginBase):
    # model = StaffMember
    name = "Staff Member"
    module = _("Staff Members Plugin")
    render_template = "staff_member_plugin.html"
    cache = False

    def render(self, context, instance, placeholder):
        staff_members = StaffMember.objects.all()
        context.update({"staff_members": staff_members})
        return context
