from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="index"),
    path("home/", views.home2, name="base"),
    path("filter-workshops/", views.filter_workshops, name="filter_workshops"),
    path("collaborative/", views.focused_collaborative_research, name="focused"),
    path("visiting/codeofconduct/", views.codeofconduct, name="codeofconduct"),
    path("visiting/", views.visiting_view, name="visiting"),
    path("joyfulmathmatics/", views.joyfulmath_view, name="joyful"),
    path("about/", views.about_view, name="about"),
    path("resources/", views.resources_view, name="resources"),
    path("template1/", views.template1, name="template"),
    path("visitingtemplate/", views.visitingtemplate, name="visittemplate"),
    path("template2/", views.template2, name="visittemplate"),
]
