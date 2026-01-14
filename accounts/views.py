from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from .forms import ProfileEditForm
from .models import UserProfile


def accounts_root(request):
    """
    Root /accounts/ URL - redirect to dashboard if logged in, login page if not
    """
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    return redirect('accounts:login')


def login_page(request):
    """
    Login page - redirect to dashboard if already logged in
    """
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    return render(request, "accounts/login.html")


def logout_view(request):
    """
    Logout and redirect to login page
    """
    logout(request)
    messages.success(request, "You have been successfully logged out.")
    return redirect('accounts:login')


@login_required
def dashboard(request):
    # Check if user has a profile
    try:
        profile = request.user.profile
        person = profile.person
    except UserProfile.DoesNotExist:
        # Don't redirect - render error page to avoid redirect loop
        from allauth.socialaccount.models import SocialAccount
        social_accounts = SocialAccount.objects.filter(user=request.user)
        sa_info = [f"{sa.provider}: {sa.uid}" for sa in social_accounts]

        return render(request, "accounts/dashboard.html", {
            'error': f"UserProfile not found for this account. The OAuth signal may not have fired correctly.",
            'user': request.user,
            'debug_info': f"User ID: {request.user.id}, Username: {request.user.username}, Email: {request.user.email}, Social Accounts: {', '.join(sa_info) if sa_info else 'None'}",
        })
    except Exception as e:
        # Don't redirect - render error page to avoid redirect loop
        return render(request, "accounts/dashboard.html", {
            'error': f"Error accessing profile: {type(e).__name__}: {str(e)}",
            'user': request.user,
        })

    today = timezone.now().date()

    # Get user's enrollments
    upcoming_enrollments = person.enrollments.filter(
        workshop__end_date__gte=today
    ).select_related('workshop').order_by('workshop__start_date')

    past_enrollments = person.enrollments.filter(
        workshop__end_date__lt=today
    ).select_related('workshop').order_by('-workshop__end_date')

    # Calculate profile completion
    profile_fields = [
        person.first_name,
        person.last_name,
        person.email_address,
        person.institution,
        person.phone_number,
        person.mailing_address,
        person.orcid_id,
    ]
    completed_fields = sum(1 for field in profile_fields if field)
    profile_completion = int((completed_fields / len(profile_fields)) * 100)

    context = {
        'person': person,
        'upcoming_enrollments': upcoming_enrollments,
        'past_enrollments': past_enrollments,
        'upcoming_count': upcoming_enrollments.count(),
        'past_count': past_enrollments.count(),
        'profile_completion': profile_completion,
    }

    return render(request, "accounts/dashboard.html", context)


@login_required
def edit_profile(request):
    person = request.user.profile.person
    if request.method == "POST":
        form = ProfileEditForm(request.POST, instance=person)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("accounts:dashboard")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProfileEditForm(instance=person)

    return render(request, "accounts/profile_form.html", {"form": form, "person": person})
