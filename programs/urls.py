from django.urls import path
from . import views

app_name = "programs"

urlpatterns = [
    path("workshops/<int:code>/", views.program_page, name="program-page"),
    path("workshops/past/", views.past_workshops, name="past-workshops"),
    path("workshops/upcoming/", views.upcoming_workshops, name="upcoming_workshops"),
    path("squares/past/", views.past_squares, name="past-squares"),
    path("squares/<int:code>/", views.square_detail, name="square-detail"),
    path("communities/", views.communities, name="communities"),
    path("communities/<int:code>/", views.program_page, name="community-detail"),
]
