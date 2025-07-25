import os
from django.conf import settings
from django.contrib import admin
from django.utils.html import format_html
from .models import ReimbursementForm, TravelExpense, Event
from PyPDF2 import PdfMerger
from PIL import Image
from django.http import HttpResponse
from django.urls import reverse, path
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "view_uploads")
    search_fields = ("name",)
    ordering = ("start_date",)

    def view_uploads(self, obj):
        url = reverse("admin:view_event_uploads", args=[obj.pk])
        return format_html(f'<a href="{url}">View Uploads</a>')

    view_uploads.short_description = "Uploads"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:pk>/uploads/",
                self.admin_site.admin_view(self.view_event_uploads),
                name="view_event_uploads",
            ),
        ]
        return custom_urls + urls

    def view_event_uploads(self, request, pk):
        event = Event.objects.get(pk=pk)
        reimbursements = event.reimbursementform_set.all()
        return render(
            request,
            "event_uploads.html",
            {
                "event": event,
                "reimbursements": reimbursements,
            },
        )


@admin.action(description="Combine receipts into a single PDF")
def combine_receipts(modeladmin, request, queryset):
    output_dir = os.path.join(settings.MEDIA_ROOT, "merged_pdfs")
    os.makedirs(output_dir, exist_ok=True)

    for form in queryset:
        merger = PdfMerger()
        temp_files = []

        # Collect receipts from expenses
        for expense in form.expenses.all():
            if expense.receipt:
                file_path = expense.receipt.path
                ext = file_path.split(".")[-1].lower()

                # If PDF, add directly
                if ext == "pdf":
                    merger.append(file_path)
                # If image, convert to PDF first
                elif ext in ["jpg", "jpeg", "png"]:
                    img = Image.open(file_path).convert("RGB")
                    temp_pdf_path = os.path.join(
                        output_dir, f"{os.path.basename(file_path)}.pdf"
                    )
                    img.save(temp_pdf_path)
                    merger.append(temp_pdf_path)
                    temp_files.append(temp_pdf_path)

        # Save combined PDF
        output_file = os.path.join(
            output_dir, f"{form.name.replace(' ', '_')}_receipts.pdf"
        )
        with open(output_file, "wb") as f:
            merger.write(f)

        # Cleanup temp files
        for tmp in temp_files:
            if os.path.exists(tmp):
                os.remove(tmp)

        modeladmin.message_user(request, f"Combined PDF created: {output_file}")


class TravelExpenseInline(admin.TabularInline):
    model = TravelExpense
    extra = 0


class ReimbursementFormAdmin(admin.ModelAdmin):
    list_display = ("name", "event", "created_at", "download_pdf_button")
    list_filter = ("event",)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:pk>/download-pdf/",
                self.admin_site.admin_view(self.download_combined_pdf),
                name="reimbursements_reimbursementform_download_pdf",  # custom name
            ),
        ]
        return custom_urls + urls

    def download_pdf_button(self, obj):
        url = reverse(
            "admin:reimbursements_reimbursementform_download_pdf", args=[obj.pk]
        )
        return format_html(f'<a class="button" href="{url}">Download Combined PDF</a>')

    download_pdf_button.short_description = "Receipts PDF"

    def download_combined_pdf(self, request, pk):
        obj = self.get_object(request, pk)
        merger = PdfMerger()

        # ✅ Add visa-related PDFs if they exist
        if obj.most_recent_i94 and obj.most_recent_i94.path.endswith(".pdf"):
            merger.append(obj.most_recent_i94.path)
        if obj.travel_history_i94 and obj.travel_history_i94.path.endswith(".pdf"):
            merger.append(obj.travel_history_i94.path)
        if obj.passport_copy and obj.passport_copy.path.endswith(".pdf"):
            merger.append(obj.passport_copy.path)

        # ✅ Add all receipt PDFs from expenses
        for exp in obj.expenses.all():  # Use related_name="expenses" for cleaner code
            if exp.receipt and exp.receipt.path.endswith(".pdf"):
                merger.append(exp.receipt.path)

        # ✅ Serve merged file
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="{obj.name}_combined.pdf"'
        )
        merger.write(response)
        merger.close()
        return response


admin.site.register(ReimbursementForm, ReimbursementFormAdmin)
admin.site.register(TravelExpense)
