from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone


def login_page(request):
    # just a landing page template
    return render(request, "accounts/login.html")


@login_required
def dashboard(request):
    person = request.user.profile.person
    today = timezone.now().date()

    return render(
        request,
        "accounts/dashboard.html",
    )


@login_required
def edit_profile(request):
    person = request.user.profile.person
    if request.method == "POST":
        person.institution = request.POST.get("institution") or person.institution
        person.email = request.POST.get("email") or person.email
        person.save()
        messages.success(request, "Profile updated.")
        return redirect("accounts:dashboard")
    return render(request, "accounts/profile_form.html", {"person": person})
