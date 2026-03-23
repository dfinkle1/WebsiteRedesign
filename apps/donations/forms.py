from django import forms

from .models import DonationCategory


class DonationForm(forms.Form):
    donor_name = forms.CharField(
        max_length=200,
        label="Full Name",
        widget=forms.TextInput(attrs={"placeholder": "Jane Smith", "class": "form-control"}),
        error_messages={
            "required": "Please enter your full name.",
        },
    )
    donor_email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(attrs={"placeholder": "jane@example.com", "class": "form-control"}),
        error_messages={
            "required": "Please enter your email address.",
            "invalid": "Please enter a valid email address.",
        },
    )
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=1,
        label="Donation Amount ($)",
        widget=forms.NumberInput(attrs={"placeholder": "100.00", "class": "form-control", "step": "0.01"}),
        error_messages={
            "required": "Please enter a donation amount.",
            "invalid": "Please enter a valid dollar amount.",
            "min_value": "Minimum donation amount is $1.",
        },
    )
    category = forms.ModelChoiceField(
        queryset=DonationCategory.objects.filter(is_active=True),
        label="Designation",
        empty_label="Select a fund",
        widget=forms.Select(attrs={"class": "form-select"}),
        error_messages={
            "required": "Please select a fund.",
            "invalid_choice": "Please select a valid fund.",
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # After form is bound and validated, add Bootstrap's is-invalid class
        # to any field that has errors so the red border appears automatically.
        if self.is_bound:
            for field_name in self.fields:
                if self[field_name].errors:
                    existing = self.fields[field_name].widget.attrs.get("class", "")
                    self.fields[field_name].widget.attrs["class"] = f"{existing} is-invalid".strip()

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount > 100_000:
            raise forms.ValidationError("Please contact us directly for gifts over $100,000.")
        return amount
