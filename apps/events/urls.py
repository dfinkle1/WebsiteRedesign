from django.urls import path
from . import views

app_name = "events"

urlpatterns = [
    path("", views.event_list, name="event-list"),
    path("<slug:slug>/", views.event_detail, name="event-detail"),
    path("<slug:slug>/ical/", views.event_ical, name="event-ical"),
]
