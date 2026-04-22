from django.urls import path
from . import views

app_name = "timeeffort"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("week/<int:week_id>/", views.weekly_entry, name="weekly_entry"),
    path("period/<int:period_id>/", views.period_summary, name="period_summary"),
    path("period/<int:period_id>/describe/", views.final_report_describe, name="final_report_describe"),
    path("download/weekly/<int:timesheet_id>/", views.download_weekly_pdf, name="download_weekly_pdf"),
    path("download/final/<int:report_id>/", views.download_final_pdf, name="download_final_pdf"),
    # Director
    path("director/defaults/", views.director_set_defaults, name="director_set_defaults"),
    path("director/period/<int:period_id>/", views.director_period_entry, name="director_period_entry"),
    path("download/director/<int:submission_id>/", views.download_director_pdf, name="download_director_pdf"),
]
