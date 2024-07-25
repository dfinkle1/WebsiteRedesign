from django import forms
from .models import StaffMember


class StaffMemberForm(forms.ModelForm):
    class Meta:
        model = StaffMember
        fields = ["name", "role", "bio", "staff_photo", "more_info_link"]
