from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="index"),
    path("home/", views.home2, name="base"),
    path("filter-workshops/", views.filter_workshops, name="filter_workshops"),
]
