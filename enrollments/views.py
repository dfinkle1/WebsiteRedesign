from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import Enrollment, ProgramInvitation
from programs.models import Program


def invitation_respond(request, token):
    """
    View for responding to a program invitation.

    GET: Show invitation details and accept/decline options
    POST: Process accept or decline action
    """
    invitation = get_object_or_404(
        ProgramInvitation.objects.select_related('program'),
        token=token,
    )

    # Check if invitation is still valid
    if invitation.status != ProgramInvitation.Status.PENDING:
        return render(request, 'enrollments/invitation_already_responded.html', {
            'invitation': invitation,
        })

    if invitation.is_expired:
        return render(request, 'enrollments/invitation_expired.html', {
            'invitation': invitation,
        })

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'decline':
            invitation.decline()
            messages.info(request, f"You have declined the invitation to {invitation.program.title}.")
            return redirect('accounts:dashboard') if request.user.is_authenticated else redirect('accounts:login')

        elif action == 'accept':
            # User must be logged in to accept
            if not request.user.is_authenticated:
                # Store token in session and redirect to login
                request.session['pending_invitation_token'] = token
                messages.info(request, "Please sign in to accept this invitation.")
                return redirect('accounts:login')

            # Get or verify person record
            try:
                person = request.user.profile.person
            except AttributeError:
                messages.error(request, "Your account is not linked to a participant profile. Please contact support.")
                return redirect('accounts:dashboard')

            # Check if already enrolled in this program
            if Enrollment.objects.filter(person=person, workshop=invitation.program).exists():
                messages.warning(request, f"You are already enrolled in {invitation.program.title}.")
                invitation.status = ProgramInvitation.Status.ACCEPTED
                invitation.accepted_at = timezone.now()
                invitation.person = person
                invitation.save()
                return redirect('accounts:dashboard')

            # Create enrollment
            enrollment = Enrollment.objects.create(
                person=person,
                workshop=invitation.program,
                source=Enrollment.Source.INVITATION,
                first_name=person.first_name,
                middle_name=person.middle_name,
                last_name=person.last_name,
                email_snap=person.email_address,
                orcid_snap=person.orcid_id,
                institution=person.institution,
                accepted_at=timezone.now(),
            )

            # Mark invitation as accepted
            invitation.accept(person, enrollment)

            messages.success(request, f"You have accepted the invitation to {invitation.program.title}!")

            # Redirect to enrollment details form to complete logistics
            return redirect('enrollments:enrollment_details', enrollment_id=enrollment.id)

    return render(request, 'enrollments/invitation_respond.html', {
        'invitation': invitation,
        'program': invitation.program,
    })


@login_required
def enrollment_details(request, enrollment_id):
    """
    Form for viewing/editing enrollment logistics (airports, contact info, etc).
    Works for both accepted enrollments and pending applications.
    """
    try:
        person = request.user.profile.person
    except AttributeError:
        messages.error(request, "Your account is not linked to a participant profile.")
        return redirect('accounts:dashboard')

    enrollment = get_object_or_404(
        Enrollment.objects.select_related('workshop'),
        id=enrollment_id,
        person=person,
    )

    # Determine enrollment status for template
    is_accepted = enrollment.accepted_at is not None
    is_pending = enrollment.accepted_at is None and enrollment.declined_at is None
    is_declined = enrollment.declined_at is not None

    # Can only edit if not declined
    can_edit = not is_declined

    if request.method == 'POST' and can_edit:
        # Update logistics fields
        check_in = request.POST.get('check_in_date', '').strip()
        check_out = request.POST.get('check_out_date', '').strip()
        enrollment.check_in_date = check_in if check_in else None
        enrollment.check_out_date = check_out if check_out else None
        enrollment.phone_number = request.POST.get('phone_number', '').strip()
        enrollment.mailing_address = request.POST.get('mailing_address', '').strip()
        enrollment.notes = request.POST.get('notes', '').strip()
        enrollment.save()

        messages.success(request, "Your details have been saved.")
        return redirect('accounts:dashboard')

    return render(request, 'enrollments/enrollment_details.html', {
        'enrollment': enrollment,
        'program': enrollment.workshop,
        'is_accepted': is_accepted,
        'is_pending': is_pending,
        'is_declined': is_declined,
        'can_edit': can_edit,
    })


@login_required
def withdraw_enrollment(request, enrollment_id):
    """
    Allow a user to withdraw from an accepted enrollment.
    Only allowed before the program starts.
    """
    try:
        person = request.user.profile.person
    except AttributeError:
        messages.error(request, "Your account is not linked to a participant profile.")
        return redirect('accounts:dashboard')

    enrollment = get_object_or_404(
        Enrollment.objects.select_related('workshop'),
        id=enrollment_id,
        person=person,
    )

    program = enrollment.workshop
    today = timezone.now().date()

    # Can only withdraw from accepted enrollments
    if not enrollment.accepted_at:
        messages.error(request, "You can only withdraw from accepted enrollments.")
        return redirect('accounts:dashboard')

    # Can only withdraw before program starts
    if program.start_date and program.start_date <= today:
        messages.error(request, "You cannot withdraw after the program has started. Please contact staff.")
        return redirect('accounts:dashboard')

    # Already withdrawn
    if enrollment.declined_at:
        messages.info(request, "You have already withdrawn from this program.")
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        confirm = request.POST.get('confirm')

        if confirm:
            enrollment.declined_at = timezone.now()
            enrollment.declined_reason = f"Withdrawn by participant: {reason}" if reason else "Withdrawn by participant"
            enrollment.save(update_fields=['declined_at', 'declined_reason'])

            messages.success(request, f"You have withdrawn from {program.title}.")
            return redirect('accounts:dashboard')

    return render(request, 'enrollments/withdraw_enrollment.html', {
        'enrollment': enrollment,
        'program': program,
    })


@login_required
def program_apply(request, program_code):
    """
    Apply to a program that has open applications.
    """
    program = get_object_or_404(Program, code=program_code)

    # Check if program is accepting applications
    if not program.is_accepting_applications:
        messages.error(request, "This program is not currently accepting applications.")
        return redirect('programs:program-page', code=program_code)

    try:
        person = request.user.profile.person
    except AttributeError:
        messages.error(request, "Your account is not linked to a participant profile. Please contact support.")
        return redirect('programs:program-page', code=program_code)

    # Check if already enrolled
    existing = Enrollment.objects.filter(person=person, workshop=program).first()
    if existing:
        messages.info(request, f"You have already applied to {program.title}.")
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        # Create enrollment as an application
        check_in = request.POST.get('check_in_date', '').strip()
        check_out = request.POST.get('check_out_date', '').strip()
        enrollment = Enrollment.objects.create(
            person=person,
            workshop=program,
            source=Enrollment.Source.APPLICATION,
            first_name=person.first_name,
            middle_name=person.middle_name,
            last_name=person.last_name,
            email_snap=person.email_address,
            orcid_snap=person.orcid_id,
            institution=person.institution,
            # Note: accepted_at is NOT set - this is a pending application
            check_in_date=check_in if check_in else None,
            check_out_date=check_out if check_out else None,
            phone_number=request.POST.get('phone_number', '').strip(),
            mailing_address=request.POST.get('mailing_address', '').strip(),
            notes=request.POST.get('notes', '').strip(),
        )

        messages.success(request, f"Your application to {program.title} has been submitted!")
        return redirect('accounts:dashboard')

    return render(request, 'enrollments/program_apply.html', {
        'program': program,
        'person': person,
    })
