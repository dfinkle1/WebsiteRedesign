from django.urls import path
from . import views

app_name = "programs"

urlpatterns = [
    path("workshops/<int:code>/", views.program_page, name="program-page"),
    path("workshops/past/", views.past_workshops, name="past-workshops"),
    path("workshops/upcoming/", views.upcoming_workshops, name="upcoming_workshops"),
]
