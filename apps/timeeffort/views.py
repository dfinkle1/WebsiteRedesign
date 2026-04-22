from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.forms import modelformset_factory
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import DirectorDefaultsForm, DirectorPeriodEntryForm, PeriodDescribeForm, WeeklyTimesheetLineFormSet, ZeroWeekConfirmForm
from .models import (
    AIMHoliday,
    DirectorDefaultAllocation,
    DirectorPeriodSubmission,
    DirectorSubmissionLine,
    PDFSnapshot,
    PeriodReport,
    PeriodReportLine,
    ReportingPeriod,
    ReportingWeek,
    StaffTimesheetProfile,
    WeeklyTimesheet,
    WeeklyTimesheetLine,
)
from .services import (
    count_holidays_in_period,
    generate_director_pdf,
    generate_weekly_pdf,
    initialize_period_report,
    validate_period_percentages,
)


def _get_staff_profile(request):
    """Returns the StaffTimesheetProfile for the logged-in user, or None."""
    try:
        return request.user.timesheet_profile
    except StaffTimesheetProfile.DoesNotExist:
        return None


# =============================================================================
# DASHBOARD
# =============================================================================


@login_required
def dashboard(request):
    profile = _get_staff_profile(request)
    if not profile:
        return render(request, "timeeffort/no_profile.html")

    if profile.staff_type == StaffTimesheetProfile.StaffType.DIRECTOR:
        return _director_dashboard(request, profile)

    # Active periods for this staff type
    active_periods = ReportingPeriod.objects.filter(
        staff_type=profile.staff_type,
        is_locked=False,
    ).prefetch_related("weeks")

    period_summaries = []
    for period in active_periods:
        weeks = period.weeks.all()
        submitted_ids = WeeklyTimesheet.objects.filter(
            staff=profile,
            week__in=weeks,
            status=WeeklyTimesheet.Status.SUBMITTED,
        ).values_list("week_id", flat=True)

        outstanding = weeks.exclude(id__in=submitted_ids)

        period_summaries.append(
            {
                "period": period,
                "total_weeks": weeks.count(),
                "submitted_count": len(submitted_ids),
                "outstanding_weeks": outstanding,
            }
        )

    recent_reports = PeriodReport.objects.filter(
        staff=profile,
        status=PeriodReport.Status.GENERATED,
    ).select_related("period").order_by("-period__start_date")[:3]

    return render(
        request,
        "timeeffort/dashboard.html",
        {
            "profile": profile,
            "period_summaries": period_summaries,
            "recent_reports": recent_reports,
        },
    )


# =============================================================================
# WEEKLY ENTRY
# =============================================================================


@login_required
def weekly_entry(request, week_id):
    profile = _get_staff_profile(request)
    if not profile:
        raise Http404

    week = get_object_or_404(ReportingWeek, pk=week_id)

    if week.period.is_locked:
        messages.error(request, "This reporting period is locked.")
        return redirect("timeeffort:dashboard")

    # Get or create the timesheet
    timesheet, _ = WeeklyTimesheet.objects.get_or_create(
        staff=profile,
        week=week,
        defaults={"status": WeeklyTimesheet.Status.DRAFT},
    )

    edits_allowed = week.period.edits_allowed

    if timesheet.status == WeeklyTimesheet.Status.SUBMITTED and not edits_allowed:
        return render(request, "timeeffort/weekly_entry_locked.html", {"timesheet": timesheet, "week": week})

    initial, num_preset_rows = _build_initial_for_week(profile, week)

    if request.method == "POST":
        action = request.POST.get("action", "save")

        if action == "confirm_zero":
            zero_form = ZeroWeekConfirmForm(request.POST)
            if zero_form.is_valid():
                timesheet.zero_week_reason = zero_form.cleaned_data["zero_week_reason"]
                timesheet.submit()
                messages.success(request, f"Week of {week.start_date} confirmed as zero-hour and submitted.")
                return redirect("timeeffort:dashboard")
            formset = WeeklyTimesheetLineFormSet(initial=initial, prefix="lines")
            return render(request, "timeeffort/weekly_entry.html", {
                "timesheet": timesheet, "week": week, "formset": formset,
                "zero_form": zero_form, "show_zero_modal": True,
                "num_preset_rows": num_preset_rows,
                "day_labels": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                "edits_allowed": edits_allowed,
                "submission_deadline": week.period.submission_deadline,
            })

        formset = WeeklyTimesheetLineFormSet(request.POST, prefix="lines")
        if formset.is_valid():
            timesheet.lines.all().delete()
            for form in formset:
                if form.cleaned_data.get("DELETE"):
                    continue
                activity = form.cleaned_data.get("activity")
                if not activity:
                    continue
                WeeklyTimesheetLine.objects.create(
                    timesheet=timesheet,
                    activity=activity,
                    grant_code=form.cleaned_data.get("grant_code", ""),
                    hours_sun=form.cleaned_data.get("hours_sun") or Decimal("0"),
                    hours_mon=form.cleaned_data.get("hours_mon") or Decimal("0"),
                    hours_tue=form.cleaned_data.get("hours_tue") or Decimal("0"),
                    hours_wed=form.cleaned_data.get("hours_wed") or Decimal("0"),
                    hours_thu=form.cleaned_data.get("hours_thu") or Decimal("0"),
                    hours_fri=form.cleaned_data.get("hours_fri") or Decimal("0"),
                    hours_sat=form.cleaned_data.get("hours_sat") or Decimal("0"),
                    description=form.cleaned_data.get("description", ""),
                )

            if action == "submit":
                total = timesheet.total_hours
                if total == 0:
                    zero_form = ZeroWeekConfirmForm()
                    new_initial, num_preset_rows = _build_initial_for_week(profile, week)
                    formset = WeeklyTimesheetLineFormSet(initial=new_initial, prefix="lines")
                    return render(request, "timeeffort/weekly_entry.html", {
                        "timesheet": timesheet, "week": week, "formset": formset,
                        "zero_form": zero_form, "show_zero_modal": True,
                        "num_preset_rows": num_preset_rows,
                        "day_labels": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                    })
                timesheet.submit()
                messages.success(request, f"Week of {week.start_date} submitted successfully.")
                return redirect("timeeffort:dashboard")

            messages.success(request, "Draft saved.")
            return redirect("timeeffort:weekly_entry", week_id=week.id)
    else:
        formset = WeeklyTimesheetLineFormSet(initial=initial, prefix="lines")

    zero_form = ZeroWeekConfirmForm()
    return render(
        request,
        "timeeffort/weekly_entry.html",
        {
            "timesheet": timesheet,
            "week": week,
            "profile": profile,
            "formset": formset,
            "zero_form": zero_form,
            "show_zero_modal": False,
            "num_preset_rows": num_preset_rows,
            "day_labels": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
            "edits_allowed": edits_allowed,
            "submission_deadline": week.period.submission_deadline,
        },
    )


def _zero_to_none(value):
    """Render zero hours as blank so users don't have to delete a 0 before typing."""
    return None if not value else value


def _line_to_initial(line):
    return {
        "activity": line.activity_id,
        "grant_code": line.grant_code,
        "hours_sun": _zero_to_none(line.hours_sun),
        "hours_mon": _zero_to_none(line.hours_mon),
        "hours_tue": _zero_to_none(line.hours_tue),
        "hours_wed": _zero_to_none(line.hours_wed),
        "hours_thu": _zero_to_none(line.hours_thu),
        "hours_fri": _zero_to_none(line.hours_fri),
        "hours_sat": _zero_to_none(line.hours_sat),
        "description": line.description,
    }


def _blank_initial(activity):
    return {
        "activity": activity.id,
        "grant_code": activity.default_grant_code,
        "hours_sun": None,
        "hours_mon": None,
        "hours_tue": None,
        "hours_wed": None,
        "hours_thu": None,
        "hours_fri": None,
        "hours_sat": None,
        "description": "",
    }


def _build_initial_for_week(profile, week):
    """
    Build ordered initial form data for a weekly entry.

    Row order:
    1. Preset activities (always shown, cannot be removed)
    2. Non-preset activities carried forward from earlier weeks in this period
    3. Any non-preset lines already saved to this specific week (e.g. added mid-period)

    Returns (initial_list, num_preset_rows) so the template knows which rows are locked.
    """
    from .models import Activity

    preset_activities = list(
        Activity.objects.filter(is_preset=True, is_active=True).order_by("sort_order", "name")
    )

    # Existing lines for this week: keyed by (activity_id, grant_code)
    existing_lines = {}
    try:
        ts = WeeklyTimesheet.objects.get(staff=profile, week=week)
        for line in ts.lines.select_related("activity").all():
            existing_lines[(line.activity_id, line.grant_code)] = line
    except WeeklyTimesheet.DoesNotExist:
        pass

    # Non-preset activities used in earlier weeks of this period (carry-forward)
    earlier_weeks = week.period.weeks.filter(week_number__lt=week.week_number)
    carried_keys = []
    if earlier_weeks.exists():
        carried = (
            WeeklyTimesheetLine.objects.filter(
                timesheet__staff=profile,
                timesheet__week__in=earlier_weeks,
                activity__is_preset=False,
            )
            .values("activity_id", "grant_code")
            .distinct()
            .order_by("activity__sort_order", "activity__name")
        )
        carried_keys = [(c["activity_id"], c["grant_code"]) for c in carried]

    initial = []
    seen_keys = set()

    # 1. Preset rows (locked)
    for activity in preset_activities:
        # Grant addon presets may appear multiple times with different grant codes
        # if the user saved a specific grant code last time.
        matching = [(k, v) for k, v in existing_lines.items() if k[0] == activity.id]
        if matching:
            for key, line in matching:
                seen_keys.add(key)
                initial.append(_line_to_initial(line))
        else:
            key = (activity.id, activity.default_grant_code)
            seen_keys.add(key)
            initial.append(_blank_initial(activity))

    num_preset_rows = len(initial)

    # 2. Carried-forward non-preset rows
    for (act_id, grant_code) in carried_keys:
        key = (act_id, grant_code)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        line = existing_lines.get(key)
        initial.append(_line_to_initial(line) if line else {
            "activity": act_id,
            "grant_code": grant_code,
            "hours_sun": Decimal("0"), "hours_mon": Decimal("0"),
            "hours_tue": Decimal("0"), "hours_wed": Decimal("0"),
            "hours_thu": Decimal("0"), "hours_fri": Decimal("0"),
            "hours_sat": Decimal("0"), "description": "",
        })

    # 3. Any custom rows saved this week that weren't in carry-forward
    for key, line in existing_lines.items():
        if key not in seen_keys:
            initial.append(_line_to_initial(line))

    return initial, num_preset_rows


# =============================================================================
# PERIOD SUMMARY
# =============================================================================


@login_required
def period_summary(request, period_id):
    profile = _get_staff_profile(request)
    if not profile:
        raise Http404

    period = get_object_or_404(ReportingPeriod, pk=period_id)
    weeks = period.weeks.all()

    week_statuses = []
    for week in weeks:
        ts = WeeklyTimesheet.objects.filter(staff=profile, week=week).first()
        week_statuses.append({"week": week, "timesheet": ts})

    all_submitted = bool(week_statuses) and all(
        ws["timesheet"] and ws["timesheet"].status == WeeklyTimesheet.Status.SUBMITTED
        for ws in week_statuses
    )

    report = PeriodReport.objects.filter(staff=profile, period=period).first()
    latest_pdf = None
    if report:
        latest_pdf = report.pdfs.filter(pdf_type=PDFSnapshot.PDFType.FINAL).order_by("-version").first()

    return render(
        request,
        "timeeffort/period_summary.html",
        {
            "period": period,
            "profile": profile,
            "week_statuses": week_statuses,
            "all_submitted": all_submitted,
            "report": report,
            "latest_pdf": latest_pdf,
        },
    )


# =============================================================================
# FINAL REPORT DESCRIBE + GENERATE
# =============================================================================


@login_required
def final_report_describe(request, period_id):
    """
    Intermediate step: show the rollup and let staff enter duties descriptions
    per activity before generating the PDF.
    """
    profile = _get_staff_profile(request)
    if not profile:
        raise Http404

    period = get_object_or_404(ReportingPeriod, pk=period_id)

    # Check weeks directly — PeriodReport may not exist yet on first visit
    period_weeks = period.weeks.all()
    submitted_count = WeeklyTimesheet.objects.filter(
        staff=profile,
        week__in=period_weeks,
        status=WeeklyTimesheet.Status.SUBMITTED,
    ).count()

    if submitted_count < period_weeks.count():
        messages.error(request, "All weeks must be submitted before generating the final report.")
        return redirect("timeeffort:period_summary", period_id=period_id)

    # Get or initialize the period report
    report = PeriodReport.objects.filter(staff=profile, period=period).first()
    if not report or report.status == PeriodReport.Status.PENDING:
        report = initialize_period_report(profile, period)

    DescribeFormSet = modelformset_factory(
        PeriodReportLine,
        form=PeriodDescribeForm,
        extra=0,
    )

    if request.method == "POST":
        formset = DescribeFormSet(request.POST, queryset=report.lines.order_by("sort_order"))
        if formset.is_valid():
            formset.save()
            report.refresh_from_db()
            # Validate percentages before allowing generation
            lines = report.lines.all()
            rows = [{"percentage": l.percentage} for l in lines]
            if not validate_period_percentages([{"percentage": l.percentage} for l in lines]):
                messages.error(
                    request,
                    f"Percentages do not sum to 100% (got "
                    f"{sum(l.percentage for l in lines):.2f}%). Contact an admin."
                )
                return redirect("timeeffort:final_report_describe", period_id=period_id)

            from .services import generate_final_pdf
            generate_final_pdf(report, generated_by=request.user)
            messages.success(request, "Final report generated. You can now download your PDF.")
            return redirect("timeeffort:period_summary", period_id=period_id)
    else:
        formset = DescribeFormSet(queryset=report.lines.order_by("sort_order"))

    return render(
        request,
        "timeeffort/final_report_describe.html",
        {
            "period": period,
            "profile": profile,
            "report": report,
            "formset": formset,
        },
    )


# =============================================================================
# PDF DOWNLOAD
# =============================================================================


@login_required
def download_weekly_pdf(request, timesheet_id):
    profile = _get_staff_profile(request)
    if not profile:
        raise Http404

    timesheet = get_object_or_404(WeeklyTimesheet, pk=timesheet_id, staff=profile)

    if timesheet.status != WeeklyTimesheet.Status.SUBMITTED:
        messages.error(request, "Weekly report can only be downloaded after submission.")
        return redirect("timeeffort:weekly_entry", week_id=timesheet.week_id)

    snapshot = timesheet.pdfs.filter(pdf_type=PDFSnapshot.PDFType.WEEKLY).order_by("-version").first()
    if not snapshot:
        snapshot = generate_weekly_pdf(timesheet, generated_by=request.user)

    return _serve_pdf(snapshot, f"weekly_report_{timesheet.week.start_date}.pdf")


@login_required
def download_final_pdf(request, report_id):
    profile = _get_staff_profile(request)
    if not profile:
        raise Http404

    report = get_object_or_404(PeriodReport, pk=report_id, staff=profile)
    snapshot = report.pdfs.filter(pdf_type=PDFSnapshot.PDFType.FINAL).order_by("-version").first()

    if not snapshot:
        messages.error(request, "No PDF has been generated yet.")
        return redirect("timeeffort:period_summary", period_id=report.period_id)

    filename = f"effort_report_{report.period.start_date}_{report.period.end_date}.pdf"
    return _serve_pdf(snapshot, filename)


def _serve_pdf(snapshot, filename):
    try:
        snapshot.file.open("rb")
        content = snapshot.file.read()
        snapshot.file.close()
    except Exception:
        raise Http404("PDF file not found.")

    response = HttpResponse(content, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


# =============================================================================
# DIRECTOR VIEWS
# =============================================================================


def _director_dashboard(request, profile):
    active_periods = ReportingPeriod.objects.filter(
        staff_type=ReportingPeriod.StaffType.SALARY,
        is_locked=False,
    ).order_by("-start_date")

    period_summaries = []
    for period in active_periods:
        submission = DirectorPeriodSubmission.objects.filter(staff=profile, period=period).first()
        holiday_count = count_holidays_in_period(period)
        period_summaries.append({
            "period": period,
            "submission": submission,
            "holiday_count": holiday_count,
            "holiday_pct": holiday_count * 5,
        })

    has_defaults = DirectorDefaultAllocation.objects.filter(profile=profile).exists()

    recent_pdfs = PDFSnapshot.objects.filter(
        director_submission__staff=profile,
        pdf_type=PDFSnapshot.PDFType.DIRECTOR,
    ).select_related("director_submission__period").order_by("-generated_at")[:3]

    return render(request, "timeeffort/dashboard.html", {
        "profile": profile,
        "period_summaries": period_summaries,
        "is_director": True,
        "has_defaults": has_defaults,
        "recent_pdfs": recent_pdfs,
    })


@login_required
def director_set_defaults(request):
    profile = _get_staff_profile(request)
    if not profile or profile.staff_type != StaffTimesheetProfile.StaffType.DIRECTOR:
        raise Http404

    from .models import Activity
    primary_activity = Activity.objects.filter(sort_order=0).first()
    primary_grant_code = primary_activity.default_grant_code if primary_activity else ""

    defaults, _ = DirectorDefaultAllocation.objects.get_or_create(profile=profile)

    if request.method == "POST":
        form = DirectorDefaultsForm(request.POST, instance=defaults)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.main_grant_code = primary_grant_code
            obj.save()
            messages.success(request, "Default allocations saved.")
            return redirect("timeeffort:dashboard")
    else:
        form = DirectorDefaultsForm(instance=defaults)

    return render(request, "timeeffort/director_defaults.html", {
        "profile": profile,
        "form": form,
        "primary_grant_code": primary_grant_code,
    })


@login_required
def director_period_entry(request, period_id):
    profile = _get_staff_profile(request)
    if not profile or profile.staff_type != StaffTimesheetProfile.StaffType.DIRECTOR:
        raise Http404

    period = get_object_or_404(ReportingPeriod, pk=period_id)

    if period.is_locked:
        messages.error(request, "This reporting period is locked.")
        return redirect("timeeffort:dashboard")

    holiday_count = count_holidays_in_period(period)
    holiday_pct = Decimal(str(holiday_count * 5))
    holidays = AIMHoliday.objects.filter(date__range=[period.start_date, period.end_date])

    # Primary grant code is locked — always sourced from the Activity with sort_order=0
    from .models import Activity
    primary_activity = Activity.objects.filter(sort_order=0).first()
    main_grant_code = primary_activity.default_grant_code if primary_activity else ""

    submission, _ = DirectorPeriodSubmission.objects.get_or_create(
        staff=profile,
        period=period,
        defaults={"status": DirectorPeriodSubmission.Status.DRAFT},
    )

    edits_allowed = period.edits_allowed
    if submission.status == DirectorPeriodSubmission.Status.SUBMITTED and not edits_allowed:
        return render(request, "timeeffort/director_entry_locked.html", {
            "submission": submission,
            "period": period,
        })

    if request.method == "POST":
        action = request.POST.get("action", "save")
        form = DirectorPeriodEntryForm(request.POST, holiday_pct=holiday_pct)
        if form.is_valid():
            _save_director_lines(submission, form.cleaned_data, holiday_pct, main_grant_code)
            if action == "submit":
                submission.submit()
                messages.success(request, f"Effort report for {period.label} submitted.")
                return redirect("timeeffort:dashboard")
            messages.success(request, "Draft saved.")
            return redirect("timeeffort:director_period_entry", period_id=period.id)
    else:
        if submission.lines.exists():
            initial = _submission_to_form_data(submission)
        else:
            initial = _defaults_to_form_data(profile, holiday_pct)
        form = DirectorPeriodEntryForm(initial=initial, holiday_pct=holiday_pct)

    return render(request, "timeeffort/director_period_entry.html", {
        "profile": profile,
        "period": period,
        "submission": submission,
        "form": form,
        "holiday_count": holiday_count,
        "holiday_pct": holiday_pct,
        "holidays": holidays,
        "edits_allowed": edits_allowed,
        "submission_deadline": period.submission_deadline,
        "main_grant_code": main_grant_code,
    })


@login_required
def download_director_pdf(request, submission_id):
    profile = _get_staff_profile(request)
    if not profile:
        raise Http404

    submission = get_object_or_404(DirectorPeriodSubmission, pk=submission_id, staff=profile)

    if submission.status != DirectorPeriodSubmission.Status.SUBMITTED:
        messages.error(request, "Director report can only be downloaded after submission.")
        return redirect("timeeffort:director_period_entry", period_id=submission.period_id)

    snapshot = submission.pdfs.filter(pdf_type=PDFSnapshot.PDFType.DIRECTOR).order_by("-version").first()
    if not snapshot:
        snapshot = generate_director_pdf(submission, generated_by=request.user)

    filename = f"director_report_{submission.period.start_date}_{submission.period.end_date}.pdf"
    return _serve_pdf(snapshot, filename)


# --- Director helpers ---

def _defaults_to_form_data(profile, holiday_pct):
    try:
        d = profile.director_defaults
        data = {
            "main_grant_pct": max(Decimal("0"), d.main_grant_pct - holiday_pct),
            "pct_administrative": d.pct_administrative,
            "pct_other_activity": d.pct_other_activity,
            "pct_sick_personal": d.pct_sick_personal,
            "pct_vacation": d.pct_vacation,
            "pct_fundraising_pr": d.pct_fundraising_pr,
            "pct_other_unallowable": d.pct_other_unallowable,
        }
        for i in range(1, 5):
            data[f"extra_grant_code_{i}"] = getattr(d, f"extra_grant_code_{i}", "")
            data[f"extra_grant_pct_{i}"] = getattr(d, f"extra_grant_pct_{i}", Decimal("0"))
        return data
    except DirectorDefaultAllocation.DoesNotExist:
        return {}


def _submission_to_form_data(submission):
    data = {}
    for line in submission.lines.all():
        cat = line.category
        if cat == DirectorSubmissionLine.Category.DIRECT_MAIN:
            data["main_grant_pct"] = line.percentage
            data["main_grant_desc"] = line.description
        elif cat == DirectorSubmissionLine.Category.DIRECT_EXTRA:
            data[f"extra_grant_code_{line.slot}"] = line.grant_code
            data[f"extra_grant_pct_{line.slot}"] = line.percentage
            data[f"extra_grant_desc_{line.slot}"] = line.description
        elif cat == DirectorSubmissionLine.Category.IND_ADMIN:
            data["pct_administrative"] = line.percentage
            data["desc_administrative"] = line.description
        elif cat == DirectorSubmissionLine.Category.IND_OTHER:
            data["pct_other_activity"] = line.percentage
            data["desc_other_activity"] = line.description
        elif cat == DirectorSubmissionLine.Category.IND_SICK:
            data["pct_sick_personal"] = line.percentage
            data["desc_sick_personal"] = line.description
        elif cat == DirectorSubmissionLine.Category.IND_VACATION:
            data["pct_vacation"] = line.percentage
            data["desc_vacation"] = line.description
        elif cat == DirectorSubmissionLine.Category.IND_FUNDRAISING:
            data["pct_fundraising_pr"] = line.percentage
            data["desc_fundraising_pr"] = line.description
        elif cat == DirectorSubmissionLine.Category.IND_UNALLOWABLE:
            data["pct_other_unallowable"] = line.percentage
            data["desc_other_unallowable"] = line.description
    return data


def _save_director_lines(submission, cleaned, holiday_pct, main_grant_code=""):
    submission.lines.all().delete()
    # Invalidate any cached PDF so the next download regenerates with current data
    submission.pdfs.filter(pdf_type=PDFSnapshot.PDFType.DIRECTOR).delete()

    DirectorSubmissionLine.objects.create(
        submission=submission,
        category=DirectorSubmissionLine.Category.DIRECT_MAIN,
        grant_code=main_grant_code,
        percentage=cleaned.get("main_grant_pct") or Decimal("0"),
        description=cleaned.get("main_grant_desc", ""),
        slot=0,
    )

    for i in range(1, 5):
        code = cleaned.get(f"extra_grant_code_{i}", "")
        pct = cleaned.get(f"extra_grant_pct_{i}") or Decimal("0")
        if code or pct > 0:
            DirectorSubmissionLine.objects.create(
                submission=submission,
                category=DirectorSubmissionLine.Category.DIRECT_EXTRA,
                grant_code=code,
                percentage=pct,
                description=cleaned.get(f"extra_grant_desc_{i}", ""),
                slot=i,
            )

    if holiday_pct > 0:
        DirectorSubmissionLine.objects.create(
            submission=submission,
            category=DirectorSubmissionLine.Category.IND_HOLIDAY,
            percentage=holiday_pct,
            is_locked=True,
            slot=0,
        )

    indirect_map = [
        (DirectorSubmissionLine.Category.IND_ADMIN, "pct_administrative", "desc_administrative"),
        (DirectorSubmissionLine.Category.IND_OTHER, "pct_other_activity", "desc_other_activity"),
        (DirectorSubmissionLine.Category.IND_SICK, "pct_sick_personal", "desc_sick_personal"),
        (DirectorSubmissionLine.Category.IND_VACATION, "pct_vacation", "desc_vacation"),
        (DirectorSubmissionLine.Category.IND_FUNDRAISING, "pct_fundraising_pr", "desc_fundraising_pr"),
        (DirectorSubmissionLine.Category.IND_UNALLOWABLE, "pct_other_unallowable", "desc_other_unallowable"),
    ]
    for cat, pct_field, desc_field in indirect_map:
        DirectorSubmissionLine.objects.create(
            submission=submission,
            category=cat,
            percentage=cleaned.get(pct_field) or Decimal("0"),
            description=cleaned.get(desc_field, ""),
            slot=0,
        )
