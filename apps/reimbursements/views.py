import os
from django.core.files.base import ContentFile
from django.shortcuts import render
from django.utils.text import slugify
from django.core.files import File
from django.core.files.storage import FileSystemStorage
from django.utils import timezone
from formtools.wizard.views import SessionWizardView
from .models import ReimbursementForm, TravelExpense
from .forms import (
    Step1Form,
    TravelExpensePlaceholderForm,
    Step3TaxForm,
    Step4SignatureForm,
)

FORMS = [
    ("step1", Step1Form),
    (
        "expenses",
        TravelExpensePlaceholderForm,
    ),  # We'll treat this step differently (dynamic expenses)
    ("tax", Step3TaxForm),
    ("signature", Step4SignatureForm),
]

TEMPLATES = {
    "step1": "step1.html",
    "expenses": "expenses.html",
    "tax": "tax.html",
    "signature": "signature.html",
}


class ReimbursementWizard(SessionWizardView):
    form_list = FORMS

    file_storage = FileSystemStorage(location="/tmp")  # Temp storage for files

    def get_template_names(self):
        return [TEMPLATES[self.steps.current]]

    def process_step(self, form):
        step_data = super().process_step(form)

        if self.steps.current == "expenses":
            labels = self.request.POST.getlist("label[]")
            amounts = self.request.POST.getlist("amount[]")
            currencies = self.request.POST.getlist("currency[]")
            receipts = self.request.FILES.getlist("receipt[]")

            saved_paths = []
            for f in receipts:
                # ✅ Sanitize filename
                base, ext = os.path.splitext(f.name)
                safe_name = (
                    slugify(base) + ext
                )  # turns "Orders & Purchases" into "orders-purchases.pdf"
                saved_name = self.file_storage.save(safe_name, f)
                saved_paths.append(saved_name)
                print(saved_name)

            self.storage.data["_extra_data"] = {
                "labels": labels,
                "amounts": amounts,
                "currencies": currencies,
                "receipts": saved_paths,
            }

            print("DEBUG: Stored sanitized file paths:", saved_paths)

        return step_data

    # ✅ STEP 3: Final save logic
    def done(self, form_list, **kwargs):
        # ✅ Save main form
        main_form = form_list[0].save()

        # ✅ Add tax info from Step 3
        tax_data = form_list[2].cleaned_data
        for field, value in tax_data.items():
            setattr(main_form, field, value)

        # ✅ Retrieve stored expense data
        extra_data = self.storage.data.get("_extra_data", {})
        labels = extra_data.get("labels", [])
        amounts = extra_data.get("amounts", [])
        currencies = extra_data.get("currencies", [])
        receipt_paths = extra_data.get("receipts", [])

        print("DEBUG: Retrieved labels:", labels)
        print("DEBUG: Retrieved receipt paths:", receipt_paths)
        print("DEBUG: Files stored:", receipt_paths)
        for path in receipt_paths:
            print("DEBUG: Temp file exists?", self.file_storage.exists(path))

        # ✅ Create TravelExpense entries

        for i in range(len(labels)):
            receipt_file = None
            if i < len(receipt_paths):
                # ✅ Read file into memory to keep it available after 'with' closes
                with self.file_storage.open(receipt_paths[i], "rb") as f:
                    content = f.read()
                    safe_name = os.path.basename(receipt_paths[i])
                    receipt_file = ContentFile(content, name=safe_name)

                    TravelExpense.objects.create(
                        reimbursement_form=main_form,
                        label=labels[i],
                        amount=amounts[i],
                        currency=currencies[i],
                        receipt=receipt_file,  # Django will re-save it to S3
                    )

        # ✅ Signature step
        signature_data = form_list[3].cleaned_data
        main_form.signature = signature_data.get("signature")
        main_form.signed_date = timezone.now()
        main_form.save()

        return render(self.request, "success.html", {"form": main_form})
