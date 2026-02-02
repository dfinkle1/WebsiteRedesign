from django.urls import path

from . import views

app_name = "enrollments"

urlpatterns = [
    path("invite/<str:token>/", views.invitation_respond, name="invitation_respond"),
    path("enrollment/<int:enrollment_id>/details/", views.enrollment_details, name="enrollment_details"),
    path("enrollment/<int:enrollment_id>/withdraw/", views.withdraw_enrollment, name="withdraw_enrollment"),
    path("apply/<int:program_code>/", views.program_apply, name="program_apply"),
]
