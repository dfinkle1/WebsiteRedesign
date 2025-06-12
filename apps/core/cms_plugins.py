from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from cms.apphook_pool import apphook_pool
from cms.app_base import CMSApp
from django.utils.translation import gettext as _
from .models import StaffMember, NewsArticle


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


@plugin_pool.register_plugin
class NewArticlePlugin(CMSPluginBase):
    app_name = "news_article"
    name = "news article plugin"
    render_template = "newstemplate.html"

    def render(self, context, instance, placeholder):
        context = super(NewArticlePlugin, self).render(context, instance, placeholder)
        context.update({"articles": NewsArticle.objects.all()})
        return context
