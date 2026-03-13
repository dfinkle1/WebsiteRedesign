from django.contrib import admin
from django.contrib.auth import get_user_model
from django.forms import ModelChoiceField, Select, ModelForm
from django.utils.html import format_html
from adminsortable2.admin import SortableInlineAdminMixin, SortableAdminMixin
from .models import (
    ChecklistTemplate,
    ChecklistTemplateItem,
    ProgramChecklist,
    ProgramChecklistItem,
)


class ChecklistTemplateItemInlineForm(ModelForm):
    default_assignee = ModelChoiceField(
        queryset=get_user_model().objects.filter(is_staff=True).order_by("first_name", "last_name"),
        required=False,
        widget=Select,
    )

    class Meta:
        model = ChecklistTemplateItem
        fields = "__all__"


class ChecklistTemplateItemInline(SortableInlineAdminMixin, admin.TabularInline):
    model = ChecklistTemplateItem
    form = ChecklistTemplateItemInlineForm
    extra = 0
    fields = (
        "order",
        "title",
        "category",
        "default_days_before_start",
        "is_required",
        "default_assignee",
    )
    ordering = ["order"]


@admin.register(ChecklistTemplate)
class ChecklistTemplateAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ("name", "program_type", "item_count", "is_active", "created_at")
    list_filter = ("program_type", "is_active")
    search_fields = ("name",)
    inlines = [ChecklistTemplateItemInline]
    readonly_fields = ("created_at", "updated_at", "created_by")

    def item_count(self, obj):
        return obj.items.count()

    item_count.short_description = "Items"

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class ProgramChecklistItemInline(admin.TabularInline):
    model = ProgramChecklistItem
    extra = 0
    fields = ("title", "category", "assigned_to", "status", "due_date", "is_required")
    ordering = ["order", "category"]
    readonly_fields = ("template_item",)
    show_change_link = True


@admin.register(ProgramChecklist)
class ProgramChecklistAdmin(admin.ModelAdmin):
    list_display = (
        "program",
        "template_used",
        "completion_display",
        "health_display",
        "overdue_display",
        "created_at",
    )
    list_filter = ("template_used",)
    search_fields = ("program__title",)
    readonly_fields = ("created_by", "created_at", "template_used", "program")
    inlines = [ProgramChecklistItemInline]
    actions = ["sync_new_items_from_template"]

    @admin.action(description="Sync new items from template (safe — adds missing items only)")
    def sync_new_items_from_template(self, request, queryset):
        total_added = 0
        skipped = 0
        for checklist in queryset:
            if not checklist.template_used:
                skipped += 1
                continue
            total_added += checklist.sync_from_template()
        if total_added:
            self.message_user(request, f"Added {total_added} new item(s) across {queryset.count() - skipped} checklist(s).")
        else:
            self.message_user(request, "No new items to add — all checklists are already up to date.")

    def completion_display(self, obj):
        summary = obj.completion_summary()
        return f"{summary['done']}/{summary['total']} ({summary['pct']}%)"

    completion_display.short_description = "Completion"

    def health_display(self, obj):
        health = obj.health_status()
        colors = {
            "green": "#28a745",
            "yellow": "#ffc107",
            "red": "#dc3545",
            "grey": "#6c757d",
        }
        labels = {
            "green": "On Track",
            "yellow": "At Risk",
            "red": "Behind",
            "grey": "No Date",
        }
        color = colors.get(health, "#6c757d")
        label = labels.get(health, health)
        return format_html(
            '<span style="color:{}; font-weight:600;">● {}</span>', color, label
        )

    health_display.short_description = "Health"

    def overdue_display(self, obj):
        count = obj.overdue_count()
        if count:
            return format_html(
                '<span style="color:#dc3545; font-weight:600;">{} overdue</span>', count
            )
        return "—"

    overdue_display.short_description = "Overdue"


@admin.register(ProgramChecklistItem)
class ProgramChecklistItemAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "checklist",
        "assigned_to",
        "status",
        "due_date",
        "urgency_display",
        "is_required",
    )
    list_filter = ("status", "category", "is_required", "assigned_to")
    search_fields = ("title", "checklist__program__title")
    readonly_fields = (
        "template_item",
        "completed_at",
        "completed_by",
        "created_at",
        "updated_at",
    )
    autocomplete_fields = ("assigned_to",)

    def urgency_display(self, obj):
        if obj.status in ("done", "na"):
            return format_html('<span style="color:#28a745;">✓</span>', "")
        if obj.is_overdue:
            return format_html(
                '<span style="color:#dc3545; font-weight:600;">Overdue</span>', ""
            )
        days = obj.days_until_due
        if days is None:
            return "—"
        if days <= 3:
            return format_html(
                '<span style="color:#fd7e14; font-weight:600;">{} days</span>', days
            )
        if days <= 7:
            return format_html('<span style="color:#ffc107;">{} days</span>', days)
        return f"{days} days"

    urgency_display.short_description = "Due In"
