from django.contrib import admin
from .models import PDFFile
from django import forms
from django.utils.html import mark_safe


class PDFFileAdminForm(forms.ModelForm):
    class Meta:
        model = PDFFile
        fields = ["name", "file"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class PDFFileAdmin(admin.ModelAdmin):
    list_display = ["name", "file_url", "uploaded_at"]
    form = PDFFileAdminForm


admin.site.register(PDFFile, PDFFileAdmin)
