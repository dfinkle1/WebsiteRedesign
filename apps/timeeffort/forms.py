from decimal import Decimal
from django import forms
from django.forms import formset_factory

from .models import Activity, DirectorDefaultAllocation, PeriodReportLine, WeeklyTimesheet, WeeklyTimesheetLine


HOUR_FIELD_ATTRS = {
    "class": "form-control form-control-sm text-center hours-input",
    "min": "0",
    "max": "24",
    "step": "0.25",
}


class WeeklyTimesheetLineForm(forms.Form):
    """A single activity row in the weekly entry form."""

    activity = forms.ModelChoiceField(
        queryset=Activity.objects.filter(is_active=True).order_by("sort_order", "name"),
        widget=forms.Select(attrs={"class": "form-select form-select-sm activity-select"}),
        empty_label="— Select activity —",
        required=False,
    )
    grant_code = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-sm",
                "placeholder": "Grant code",
            }
        ),
    )
    hours_sun = forms.DecimalField(max_digits=4, decimal_places=2, required=False, initial=None, widget=forms.NumberInput(attrs=HOUR_FIELD_ATTRS))
    hours_mon = forms.DecimalField(max_digits=4, decimal_places=2, required=False, initial=None, widget=forms.NumberInput(attrs=HOUR_FIELD_ATTRS))
    hours_tue = forms.DecimalField(max_digits=4, decimal_places=2, required=False, initial=None, widget=forms.NumberInput(attrs=HOUR_FIELD_ATTRS))
    hours_wed = forms.DecimalField(max_digits=4, decimal_places=2, required=False, initial=None, widget=forms.NumberInput(attrs=HOUR_FIELD_ATTRS))
    hours_thu = forms.DecimalField(max_digits=4, decimal_places=2, required=False, initial=None, widget=forms.NumberInput(attrs=HOUR_FIELD_ATTRS))
    hours_fri = forms.DecimalField(max_digits=4, decimal_places=2, required=False, initial=None, widget=forms.NumberInput(attrs=HOUR_FIELD_ATTRS))
    hours_sat = forms.DecimalField(max_digits=4, decimal_places=2, required=False, initial=None, widget=forms.NumberInput(attrs=HOUR_FIELD_ATTRS))
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control form-control-sm",
                "rows": 2,
                "placeholder": "Brief description of work (optional)",
            }
        ),
    )

    def clean(self):
        cleaned = super().clean()
        activity = cleaned.get("activity")
        hours = [
            cleaned.get("hours_sun") or Decimal("0"),
            cleaned.get("hours_mon") or Decimal("0"),
            cleaned.get("hours_tue") or Decimal("0"),
            cleaned.get("hours_wed") or Decimal("0"),
            cleaned.get("hours_thu") or Decimal("0"),
            cleaned.get("hours_fri") or Decimal("0"),
            cleaned.get("hours_sat") or Decimal("0"),
        ]
        total = sum(hours)

        if activity and total == 0:
            # Allow zero-hour rows (they may be intentional for confirmed zero weeks)
            pass
        if not activity and total > 0:
            raise forms.ValidationError("Select an activity for this row.")

        # Pre-fill grant code from activity default if blank
        if activity and not cleaned.get("grant_code"):
            cleaned["grant_code"] = activity.default_grant_code

        return cleaned


WeeklyTimesheetLineFormSet = formset_factory(
    WeeklyTimesheetLineForm,
    extra=0,
    min_num=1,
    max_num=20,
    can_delete=True,
)


class ZeroWeekConfirmForm(forms.Form):
    REASONS = [
        ("", "— Select reason —"),
        ("HOLIDAY", "Company Holiday"),
        ("PTO", "Full PTO / Vacation"),
        ("LEAVE", "Leave of Absence"),
        ("OTHER", "Other"),
    ]
    zero_week_reason = forms.ChoiceField(
        choices=REASONS,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    confirm = forms.BooleanField(
        required=True,
        label="I confirm this week had zero hours worked.",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def clean_zero_week_reason(self):
        reason = self.cleaned_data.get("zero_week_reason")
        if not reason:
            raise forms.ValidationError("Please select a reason for the zero-hour week.")
        return reason


PCT_FIELD_ATTRS = {
    "class": "form-control form-control-sm text-end pct-input",
    "min": "0",
    "max": "100",
    "step": "0.01",
}

_pct = lambda: forms.DecimalField(  # noqa: E731
    max_digits=5, decimal_places=2, required=False, initial=Decimal("0"),
    widget=forms.NumberInput(attrs=PCT_FIELD_ATTRS),
)
_grant = lambda: forms.CharField(  # noqa: E731
    max_length=50, required=False,
    widget=forms.TextInput(attrs={"class": "form-control form-control-sm", "placeholder": "Grant code"}),
)
_desc = lambda: forms.CharField(  # noqa: E731
    required=False,
    widget=forms.Textarea(attrs={
        "class": "form-control form-control-sm",
        "rows": 2,
        "placeholder": "Duties / work performed",
    }),
)


class DirectorDefaultsForm(forms.ModelForm):
    class Meta:
        model = DirectorDefaultAllocation
        fields = [
            "main_grant_code",
            "main_grant_pct",
            "extra_grant_code_1", "extra_grant_pct_1",
            "extra_grant_code_2", "extra_grant_pct_2",
            "extra_grant_code_3", "extra_grant_pct_3",
            "extra_grant_code_4", "extra_grant_pct_4",
            "pct_administrative", "pct_other_activity", "pct_sick_personal",
            "pct_vacation", "pct_fundraising_pr", "pct_other_unallowable",
        ]
        widgets = {
            "main_grant_code": forms.TextInput(attrs={"class": "form-control form-control-sm", "placeholder": "e.g. DMS-2425344"}),
            "main_grant_pct": forms.NumberInput(attrs=PCT_FIELD_ATTRS),
            "extra_grant_code_1": forms.TextInput(attrs={"class": "form-control form-control-sm", "placeholder": "Grant code (optional)"}),
            "extra_grant_pct_1": forms.NumberInput(attrs=PCT_FIELD_ATTRS),
            "extra_grant_code_2": forms.TextInput(attrs={"class": "form-control form-control-sm", "placeholder": "Grant code (optional)"}),
            "extra_grant_pct_2": forms.NumberInput(attrs=PCT_FIELD_ATTRS),
            "extra_grant_code_3": forms.TextInput(attrs={"class": "form-control form-control-sm", "placeholder": "Grant code (optional)"}),
            "extra_grant_pct_3": forms.NumberInput(attrs=PCT_FIELD_ATTRS),
            "extra_grant_code_4": forms.TextInput(attrs={"class": "form-control form-control-sm", "placeholder": "Grant code (optional)"}),
            "extra_grant_pct_4": forms.NumberInput(attrs=PCT_FIELD_ATTRS),
            "pct_administrative": forms.NumberInput(attrs=PCT_FIELD_ATTRS),
            "pct_other_activity": forms.NumberInput(attrs=PCT_FIELD_ATTRS),
            "pct_sick_personal": forms.NumberInput(attrs=PCT_FIELD_ATTRS),
            "pct_vacation": forms.NumberInput(attrs=PCT_FIELD_ATTRS),
            "pct_fundraising_pr": forms.NumberInput(attrs=PCT_FIELD_ATTRS),
            "pct_other_unallowable": forms.NumberInput(attrs=PCT_FIELD_ATTRS),
        }

    def clean(self):
        cleaned = super().clean()
        pct_fields = (
            ["main_grant_pct"]
            + [f"extra_grant_pct_{i}" for i in range(1, 5)]
            + ["pct_administrative", "pct_other_activity", "pct_sick_personal",
               "pct_vacation", "pct_fundraising_pr", "pct_other_unallowable"]
        )
        total = sum(cleaned.get(f) or Decimal("0") for f in pct_fields)
        if total > Decimal("100"):
            raise forms.ValidationError(f"Default percentages sum to {total:.2f}% — cannot exceed 100%.")
        return cleaned


class DirectorPeriodEntryForm(forms.Form):
    """
    Flat form for a director's period effort submission.
    holiday_pct is injected at init (auto-calculated, not a field).
    """

    def __init__(self, *args, holiday_pct=Decimal("0"), **kwargs):
        self.holiday_pct = Decimal(str(holiday_pct))
        super().__init__(*args, **kwargs)

    main_grant_code = _grant()
    main_grant_pct = _pct()
    main_grant_desc = _desc()

    extra_grant_code_1 = _grant()
    extra_grant_pct_1 = _pct()
    extra_grant_desc_1 = _desc()
    extra_grant_code_2 = _grant()
    extra_grant_pct_2 = _pct()
    extra_grant_desc_2 = _desc()
    extra_grant_code_3 = _grant()
    extra_grant_pct_3 = _pct()
    extra_grant_desc_3 = _desc()
    extra_grant_code_4 = _grant()
    extra_grant_pct_4 = _pct()
    extra_grant_desc_4 = _desc()

    pct_administrative = _pct()
    desc_administrative = _desc()
    pct_other_activity = _pct()
    desc_other_activity = _desc()
    pct_sick_personal = _pct()
    desc_sick_personal = _desc()
    pct_vacation = _pct()
    desc_vacation = _desc()
    pct_fundraising_pr = _pct()
    desc_fundraising_pr = _desc()
    pct_other_unallowable = _pct()
    desc_other_unallowable = _desc()

    def clean(self):
        cleaned = super().clean()
        total = self.holiday_pct
        total += cleaned.get("main_grant_pct") or Decimal("0")
        for i in range(1, 5):
            total += cleaned.get(f"extra_grant_pct_{i}") or Decimal("0")
        for field in ["pct_administrative", "pct_other_activity", "pct_sick_personal",
                      "pct_vacation", "pct_fundraising_pr", "pct_other_unallowable"]:
            total += cleaned.get(field) or Decimal("0")

        if abs(total - Decimal("100")) > Decimal("0.5"):
            holiday_note = f" (includes {self.holiday_pct:.0f}% employer holiday)" if self.holiday_pct else ""
            raise forms.ValidationError(
                f"Percentages must sum to 100%. Current total: {total:.2f}%{holiday_note}."
            )
        return cleaned


class PeriodDescribeForm(forms.ModelForm):
    """Form for entering duties description on a single PeriodReportLine."""

    class Meta:
        model = PeriodReportLine
        fields = ["duties_description"]
        widgets = {
            "duties_description": forms.Textarea(
                attrs={
                    "class": "form-control form-control-sm",
                    "rows": 2,
                    "placeholder": "e.g. Meetings / excel / website",
                }
            )
        }
