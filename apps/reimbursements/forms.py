"""
Reimbursement Forms
"""

from django import forms
from django.core.exceptions import ValidationError

from .models import (
    ReimbursementRequest,
    ExpenseLineItem,
    Receipt,
    TaxStatus,
    PaymentMethod,
    ExpenseCategory,
    Currency,
)


class ReimbursementCreateForm(forms.ModelForm):
    """
    Form for creating a new reimbursement request.

    The person and submitted_by fields are set in the view, not by the user.
    """

    class Meta:
        model = ReimbursementRequest
        fields = [
            "enrollment",
            "tax_status",
            "payment_method",
            "payment_address",
            "bank_name",
            "bank_routing_number",
            "bank_account_number",
            "bank_account_type",
            "submitter_notes",
        ]
        widgets = {
            "enrollment": forms.Select(attrs={"class": "form-select"}),
            "tax_status": forms.Select(attrs={"class": "form-select"}),
            "payment_method": forms.RadioSelect(),
            "payment_address": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Street Address\nCity, State ZIP\nCountry",
                }
            ),
            "bank_name": forms.TextInput(attrs={"class": "form-control"}),
            "bank_routing_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "pattern": "[0-9]{9}",
                    "placeholder": "9-digit routing number",
                }
            ),
            "bank_account_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Account number",
                }
            ),
            "bank_account_type": forms.Select(attrs={"class": "form-select"}),
            "submitter_notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Any additional notes or context...",
                }
            ),
        }

    def __init__(self, *args, person=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Limit enrollment choices to this person's enrollments
        if person:
            self.fields["enrollment"].queryset = person.enrollments.select_related(
                "workshop"
            ).order_by("-workshop__start_date")
            self.fields["enrollment"].label_from_instance = lambda e: (
                f"{e.workshop.title} ({e.workshop.start_date.strftime('%b %Y')})"
                if e.workshop and e.workshop.start_date
                else str(e)
            )

        # Make enrollment optional
        self.fields["enrollment"].required = False
        self.fields["enrollment"].empty_label = "Not related to a specific program"

        # Payment fields are conditionally required
        self.fields["payment_address"].required = False
        self.fields["bank_name"].required = False
        self.fields["bank_routing_number"].required = False
        self.fields["bank_account_number"].required = False
        self.fields["bank_account_type"].required = False

    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get("payment_method")

        if payment_method == PaymentMethod.CHECK:
            if not cleaned_data.get("payment_address"):
                self.add_error(
                    "payment_address", "Mailing address is required for check payments."
                )

        elif payment_method == PaymentMethod.ACH:
            if not cleaned_data.get("bank_name"):
                self.add_error("bank_name", "Bank name is required for direct deposit.")
            if not cleaned_data.get("bank_routing_number"):
                self.add_error(
                    "bank_routing_number",
                    "Routing number is required for direct deposit.",
                )
            if not cleaned_data.get("bank_account_number"):
                self.add_error(
                    "bank_account_number",
                    "Account number is required for direct deposit.",
                )
            if not cleaned_data.get("bank_account_type"):
                self.add_error(
                    "bank_account_type", "Account type is required for direct deposit."
                )

        return cleaned_data


class ReimbursementEditForm(forms.ModelForm):
    """Form for editing an existing draft reimbursement."""

    class Meta:
        model = ReimbursementRequest
        fields = [
            "tax_status",
            "payment_method",
            "payment_address",
            "bank_name",
            "bank_routing_number",
            "bank_account_number",
            "bank_account_type",
            "submitter_notes",
            # Visa fields
            "citizenship_country",
            "visa_type",
            "passport_number",
            "passport_copy",
            "us_entry_date",
            "i94_document",
        ]
        widgets = {
            "tax_status": forms.Select(attrs={"class": "form-select"}),
            "payment_method": forms.RadioSelect(),
            "payment_address": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
            "bank_name": forms.TextInput(attrs={"class": "form-control"}),
            "bank_routing_number": forms.TextInput(attrs={"class": "form-control"}),
            "bank_account_number": forms.TextInput(attrs={"class": "form-control"}),
            "bank_account_type": forms.Select(attrs={"class": "form-select"}),
            "submitter_notes": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            # Visa fields
            "citizenship_country": forms.TextInput(attrs={"class": "form-control"}),
            "visa_type": forms.TextInput(attrs={"class": "form-control"}),
            "passport_number": forms.TextInput(attrs={"class": "form-control"}),
            "passport_copy": forms.FileInput(
                attrs={"class": "form-control", "accept": ".pdf,.jpg,.jpeg,.png"}
            ),
            "us_entry_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "i94_document": forms.FileInput(
                attrs={"class": "form-control", "accept": ".pdf,.jpg,.jpeg,.png"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make all optional by default, validation happens on submit
        for field in self.fields.values():
            field.required = False

    def clean_passport_copy(self):
        """Validate passport file upload."""
        from .validators import validate_uploaded_file
        file = self.cleaned_data.get('passport_copy')
        if file and hasattr(file, 'read'):  # New upload, not existing file
            validate_uploaded_file(file)
        return file

    def clean_i94_document(self):
        """Validate I-94 document upload."""
        from .validators import validate_uploaded_file
        file = self.cleaned_data.get('i94_document')
        if file and hasattr(file, 'read'):  # New upload, not existing file
            validate_uploaded_file(file)
        return file


class ExpenseLineItemForm(forms.ModelForm):
    """Form for adding/editing an expense line item."""

    class Meta:
        model = ExpenseLineItem
        fields = [
            "category",
            "description",
            "date_incurred",
            "original_currency",
            "original_amount",
            "amount_requested",
        ]
        widgets = {
            "category": forms.Select(attrs={"class": "form-select"}),
            "description": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Brief description of expense",
                }
            ),
            "date_incurred": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "original_currency": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "original_amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "Amount in original currency",
                }
            ),
            "amount_requested": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "Amount in USD",
                }
            ),
        }
        labels = {
            "original_currency": "Currency",
            "original_amount": "Amount (in selected currency)",
            "amount_requested": "Amount in USD",
        }
        help_texts = {
            "original_currency": "Select the currency you paid in",
            "original_amount": "Enter the amount as shown on your receipt",
            "amount_requested": "If USD, same as above. If foreign currency, convert to USD (staff will verify)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make original_amount optional (only needed for non-USD)
        self.fields["original_amount"].required = False

    def clean(self):
        cleaned_data = super().clean()
        currency = cleaned_data.get("original_currency")
        original_amount = cleaned_data.get("original_amount")
        amount_requested = cleaned_data.get("amount_requested")

        # If non-USD currency, original_amount should be filled
        if currency and currency != Currency.USD:
            if not original_amount:
                self.add_error(
                    "original_amount",
                    "Please enter the amount in the original currency."
                )

        # amount_requested (USD) is always required
        if not amount_requested:
            self.add_error(
                "amount_requested",
                "Please enter the USD amount."
            )

        return cleaned_data


class ReceiptUploadForm(forms.Form):
    """Form for uploading receipts to a line item."""

    file = forms.FileField(
        widget=forms.FileInput(
            attrs={
                "class": "form-control",
                "accept": ".pdf,.jpg,.jpeg,.png",
            }
        )
    )

    def clean_file(self):
        """Validate receipt file upload."""
        from .validators import validate_uploaded_file
        file = self.cleaned_data.get('file')
        if file:
            validate_uploaded_file(file)
        return file


class SubmitSignatureForm(forms.Form):
    """Form for final submission with signature."""

    signature = forms.CharField(
        max_length=255,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Type your full legal name",
            }
        ),
        help_text="By typing your name, you certify that all information is accurate.",
    )

    confirm_accuracy = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="I certify that all expenses listed are accurate and were incurred for official business.",
    )

    confirm_honoraria = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="I have not received honoraria from more than 5 institutions in the past 6 months (honorarium payments only) I declare under the penalties of perjury that all of the above information is correct.",
    )
    confirm_no_duplicate = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="I have not and will not request reimbursement for these expenses from any other source.",
    )
