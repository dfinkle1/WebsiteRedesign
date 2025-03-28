from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from django.utils.translation import gettext as _
from filer.models import File, Folder


@plugin_pool.register_plugin
class FRGPDFPlugin(CMSPluginBase):
    name = _("FRG PDF List")
    render_template = "FRG/pdf_list.html"
    cache = False

    def render(self, context, instance, placeholder):
        try:
            frg_folder = Folder.objects.get(name="FRG")
        except Folder.DoesNotExist:
            frg_folder = None

        pdf_files = (
            File.objects.filter(folder=frg_folder, file__endswith=".pdf")
            if frg_folder
            else []
        )

        context.update({"pdf_files": pdf_files})
        return context
