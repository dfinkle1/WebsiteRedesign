from django import template
from filer.models.foldermodels import Folder
from filer.models.filemodels import File

register = template.Library()


@register.inclusion_tag("newsletter_list.html")
def render_newsletters():
    try:
        folder = Folder.objects.get(name="Newsletters")
        files = folder.files.instance_of(File).filter(file__iendswith=".pdf")
    except Folder.DoesNotExist:
        files = []

    return {"newsletter_files": files}
