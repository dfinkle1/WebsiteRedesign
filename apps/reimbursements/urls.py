from django.urls import path
from . import views

app_name = "reimbursements"

urlpatterns = [
    # Dashboard
    path("", views.MyReimbursementsView.as_view(), name="my_reimbursements"),
    path("status/", views.reimbursement_status_check, name="status_check"),

    # Create new request
    path("new/", views.reimbursement_create, name="create"),

    # Single request views
    path("<int:pk>/", views.ReimbursementDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.reimbursement_edit, name="edit"),
    path("<int:pk>/submit/", views.reimbursement_submit, name="submit"),
    path("<int:pk>/cancel/", views.reimbursement_cancel, name="cancel"),

    # Expense management
    path("<int:pk>/expenses/add/", views.expense_add, name="expense_add"),
    path("<int:pk>/expenses/<int:expense_pk>/delete/", views.expense_delete, name="expense_delete"),

    # Receipt management
    path("<int:pk>/expenses/<int:expense_pk>/receipt/", views.receipt_upload, name="receipt_upload"),
    path(
        "<int:pk>/expenses/<int:expense_pk>/receipt/<int:receipt_pk>/delete/",
        views.receipt_delete,
        name="receipt_delete"
    ),
]
