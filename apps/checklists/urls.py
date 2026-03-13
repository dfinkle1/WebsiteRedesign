from django.urls import path
from . import views

app_name = "checklists"

urlpatterns = [
    # Hub — all programs health overview
    path("hub/", views.hub, name="hub"),

    # All open tasks across all programs (management view)
    path("all/", views.all_tasks, name="all_tasks"),

    # My assigned tasks
    path("mine/", views.my_tasks, name="my_tasks"),

    # Program-specific checklist
    path("program/<int:code>/", views.program_checklist, name="program_checklist"),

    # Item actions (POST only)
    path("item/<int:item_pk>/update/", views.update_checklist_item, name="update_item"),
    path("checklist/<int:checklist_pk>/add/", views.add_checklist_item, name="add_item"),
]
