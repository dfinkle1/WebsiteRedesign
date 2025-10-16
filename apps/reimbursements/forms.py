from django import forms
from .models import ReimbursementForm, TravelExpense


class Step4SignatureForm(forms.ModelForm):

    class Meta:
        model = ReimbursementForm
        fields = ["signature"]


class Step1Form(forms.ModelForm):
    class Meta:
        model = ReimbursementForm
        fields = ["event", "name", "orcid", "mailing_address"]


class TravelExpensePlaceholderForm(forms.Form):
    """Empty form so Step 2 always validates."""

    pass


class Step3TaxForm(forms.ModelForm):
    class Meta:
        model = ReimbursementForm
        fields = [
            "tax_status",
            "visa_tax_status",
            "visa_option",
            "admission_date",
            "visa_type",
            "most_recent_i94",
            "travel_history_i94",
            "passport_number",
            "passport_copy",
            "citizenship",
            "resident_of",
            "permanent_home_address",
        ]
        widgets = {
            "admission_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "visa_option": forms.TextInput(attrs={"class": "form-control"}),
            "tax_status": forms.Select(attrs={"class": "form-select"}),
            "permanent_home_address": forms.Textarea(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        tax_status = cleaned_data.get("tax_status")
        visa_tax_status = cleaned_data.get("visa_tax_status")

        # Always require tax_status
        if not tax_status:
            raise forms.ValidationError("Tax Status is required.")

        # If visa/permit selected
        if tax_status == "visa_permit":
            if not cleaned_data.get("visa_type"):
                self.add_error("visa_type", "Visa type is required.")
            if not cleaned_data.get("passport_number"):
                self.add_error("passport_number", "Passport number is required.")
            if not cleaned_data.get("most_recent_i94"):
                self.add_error("i94_upload", "I-94 upload is required.")
            if not cleaned_data.get("passport_copy"):
                self.add_error("passport_copy", "Passport upload is required.")

            # If they are a resident under Substantial Presence Test
            if visa_tax_status == "resident":
                if not cleaned_data.get("admission_date"):
                    self.add_error("admission_date", "Admission date is required.")
                if not cleaned_data.get("visa_option"):
                    self.add_error("visa_option", "Visa/Permit type is required.")
        return cleaned_data
