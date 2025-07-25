from django.contrib import admin
from .models import StaffMember
from djangocms_text.widgets import TextEditorWidget
from django import forms


class StaffMemberAdminForm(forms.ModelForm):
    # bio = forms.CharField(widget=TextEditorWidget)

    class Meta:
        model = StaffMember
        fields = "__all__"


class StaffMemberAdmin(admin.ModelAdmin):
    form = StaffMemberAdminForm
    list_display = ("name", "role", "email", "is_visible", "order")
    list_filter = ("is_visible",)
    # search_fields = ("name",)
    ordering = ("order",)


admin.site.register(StaffMember, StaffMemberAdmin)
