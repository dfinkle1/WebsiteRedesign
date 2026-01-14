from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.accounts_root, name="root"),  # /accounts/ - redirect based on login status
    path("login/", views.login_page, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("profile/", views.edit_profile, name="profile"),
]
