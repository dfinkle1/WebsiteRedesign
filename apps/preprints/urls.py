from django.urls import path

from .views import PreprintListView, PreprintYearView

app_name = "preprints"

urlpatterns = [
    path("", PreprintListView.as_view(), name="list"),
    path("<int:year>/", PreprintYearView.as_view(), name="year"),
]
