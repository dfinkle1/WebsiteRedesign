from django.contrib import admin
from adminsortable2.admin import SortableAdminMixin
from .models import StaffMember
from djangocms_text.widgets import TextEditorWidget
from django import forms


class StaffMemberAdminForm(forms.ModelForm):
    # bio = forms.CharField(widget=TextEditorWidget)

    class Meta:
        model = StaffMember
        fields = "__all__"


class StaffMemberAdmin(SortableAdminMixin, admin.ModelAdmin):
    form = StaffMemberAdminForm
    list_display = ("name", "role", "email", "is_visible", "order")
    list_filter = ("is_visible",)
    search_fields = ("name", "role")  # Enabled search for easier management
    ordering = ("order",)


admin.site.register(StaffMember, StaffMemberAdmin)
