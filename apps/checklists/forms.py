from django import forms
from django.contrib.auth import get_user_model
from .models import ChecklistTemplate, ProgramChecklistItem

User = get_user_model()


class ApplyTemplateForm(forms.Form):
    """
    Shown on the program checklist page when no checklist exists yet.
    Staff pick a template and click Apply.
    """
    template = forms.ModelChoiceField(
        queryset=ChecklistTemplate.objects.filter(is_active=True).order_by("program_type", "name"),
        label="Select Template",
        help_text="All items from this template will be copied onto this program.",
    )


class ChecklistItemUpdateForm(forms.ModelForm):
    """
    Inline update form for a single checklist item.
    Used on the program checklist page for quick status/notes updates.
    """
    class Meta:
        model = ProgramChecklistItem
        fields = ("status", "assigned_to", "due_date", "notes")
        widgets = {
            "status": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "assigned_to": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "due_date": forms.DateInput(attrs={"type": "date", "class": "form-control form-control-sm"}),
            "notes": forms.Textarea(attrs={"class": "form-control form-control-sm", "rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = User.objects.filter(is_staff=True).order_by("first_name", "last_name")
        self.fields["assigned_to"].required = False
        self.fields["due_date"].required = False
        self.fields["notes"].required = False


class AddChecklistItemForm(forms.ModelForm):
    """
    Lets coordinators manually add a one-off task to a program checklist
    that wasn't in the template.
    """
    class Meta:
        model = ProgramChecklistItem
        fields = ("title", "description", "category", "assigned_to", "due_date", "is_required", "notes")
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "assigned_to": forms.Select(attrs={"class": "form-select"}),
            "due_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = User.objects.filter(is_staff=True).order_by("first_name", "last_name")
        self.fields["assigned_to"].required = False
        self.fields["due_date"].required = False
        self.fields["description"].required = False
        self.fields["notes"].required = False
