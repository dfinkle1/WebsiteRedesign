from cms.app_base import CMSApp
from django.shortcuts import render
from filer.models import File
from filer.models import Folder


def pdf_list_view(self, request):
    try:
        frg_folder = Folder.objects.get(name="FRG")
        print(f"Found folder: {frg_folder}")  # Debugging output
    except Folder.DoesNotExist:
        frg_folder = None
        print("FRG folder not found")

    if frg_folder:
        pdf_files = frg_folder.all_files.filter(file__iendswith=".pdf")
        print(f"Found {pdf_files.count()} PDFs")  # Debugging output
        for pdf in pdf_files:
            print(f"PDF: {pdf.label}, URL: {pdf.file.url}")  # Debugging output
    else:
        pdf_files = []
        print("No PDFs found")

    return render(request, "FRG/pdf_list.html", {"pdf_files": pdf_files})
