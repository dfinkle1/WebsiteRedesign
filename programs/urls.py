from django.urls import path
from . import views

urlpatterns = [
    path("workshops/<int:code>", views.program_page, name="program-page"),
    path("", views.home, name="index"),
]
