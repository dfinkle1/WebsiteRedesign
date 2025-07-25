from django.urls import path
from .views import ReimbursementWizard, FORMS


urlpatterns = [
    path("money", ReimbursementWizard.as_view(FORMS), name="reimbursement_form"),
]
