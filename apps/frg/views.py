import logging

from cms.app_base import CMSApp
from django.shortcuts import render
from filer.models import File
from filer.models import Folder

logger = logging.getLogger(__name__)


def pdf_list_view(self, request):
    try:
        frg_folder = Folder.objects.get(name="FRG")
        logger.info(f"Found FRG folder: {frg_folder}")
    except Folder.DoesNotExist:
        frg_folder = None
        logger.warning("FRG folder not found")

    if frg_folder:
        pdf_files = frg_folder.all_files.filter(file__iendswith=".pdf")
        logger.info(f"Found {pdf_files.count()} FRG PDFs")
    else:
        pdf_files = []

    return render(request, "FRG/pdf_list.html", {"pdf_files": pdf_files})
