# cms_plugins.py
from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from programs.services import get_upcoming_workshops


@plugin_pool.register_plugin
class ProgramCardsPlugin(CMSPluginBase):
    render_template = "partials/program_cards.html"
    name = _("Program cards")

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        context["workshops"] = get_upcoming_workshops
        context["now"] = timezone.now()
        return context
