from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.forms import modelformset_factory
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    DirectorDefaultsForm,
    DirectorPeriodEntryForm,
    PeriodDescribeForm,
    WeeklyTimesheetLineFormSet,
    ZeroWeekConfirmForm,
)
from .models import (
    Activity,
    AIMHoliday,
    DirectorDefaultAllocation,
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
    generate_weekly_pdf,
    initialize_director_period_report,
    initialize_period_report,
    validate_period_percentages,
)

# Ordered day keys used throughout salary views and templates
SALARY_DAY_KEYS = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]
SALARY_DAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

# Indirect/leave/unallowable slots for salary weekly entry
# (name, classification, SalaryIndirectAllocation field name)
SALARY_INDIRECT_SLOTS = [
    ("Administrative", Activity.Classification.INDIRECT, "hours_administrative"),
    ("Other Activity", Activity.Classification.INDIRECT, "hours_other_activity"),
    ("Sick / Personal Day", Activity.Classification.LEAVE, "hours_sick_personal"),
    ("Vacation", Activity.Classification.LEAVE, "hours_vacation"),
    ("Fundraising / PR", Activity.Classification.UNALLOWABLE, "hours_fundraising_pr"),
    ("Other Unallowable", Activity.Classification.UNALLOWABLE, "hours_other_unallowable"),
]


def _get_year_filter(request):
    """
    Return (available_years, selected_year) based on existing ReportingPeriod data
    and the ?year= query param. Defaults to the current year.
    """
    available_years = list(
        ReportingPeriod.objects.values_list("start_date__year", flat=True)
        .distinct()
        .order_by("-start_date__year")
    )
    current_year = timezone.now().year
    try:
        selected_year = int(request.GET.get("year", current_year))
    except (ValueError, TypeError):
        selected_year = current_year
    if available_years and selected_year not in available_years:
        selected_year = available_years[0]  # most recent year with data
    return available_years, selected_year


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

    if profile.is_director:
        return _director_dashboard(request, profile)

    if profile.is_salary:
        return _salary_dashboard(request, profile)

    available_years, selected_year = _get_year_filter(request)

    periods = (
        ReportingPeriod.objects.filter(start_date__year=selected_year)
        .order_by("-start_date")
        .prefetch_related("weeks")
    )

    period_summaries = []
    for period in periods:
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

    recent_reports = (
        PeriodReport.objects.filter(
            staff=profile,
            status__in=[
                PeriodReport.Status.SUBMITTED,
                PeriodReport.Status.SUPERVISOR_APPROVED,
                PeriodReport.Status.PROCESSED,
            ],
        )
        .select_related("period")
        .order_by("-period__start_date")[:3]
    )

    return render(
        request,
        "timeeffort/dashboard.html",
        {
            "profile": profile,
            "period_summaries": period_summaries,
            "recent_reports": recent_reports,
            "available_years": available_years,
            "selected_year": selected_year,
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

    if profile.is_salary:
        return _salary_weekly_entry(request, profile, week)

    # Get or create the timesheet
    timesheet, _ = WeeklyTimesheet.objects.get_or_create(
        staff=profile,
        week=week,
        defaults={"status": WeeklyTimesheet.Status.DRAFT},
    )

    edits_allowed = week.period.edits_allowed

    initial, num_preset_rows = _build_initial_for_week(profile, week)

    if request.method == "POST":
        action = request.POST.get("action", "save")

        if action == "confirm_zero":
            zero_form = ZeroWeekConfirmForm(request.POST)
            if zero_form.is_valid():
                timesheet.zero_week_reason = zero_form.cleaned_data["zero_week_reason"]
                timesheet.submit()
                _invalidate_period_report_pdf(profile, week.period)
                messages.success(
                    request,
                    f"Week of {week.start_date} confirmed as zero-hour and submitted.",
                )
                return redirect("timeeffort:dashboard")
            formset = WeeklyTimesheetLineFormSet(initial=initial, prefix="lines")
            return render(
                request,
                "timeeffort/weekly_entry.html",
                {
                    "timesheet": timesheet,
                    "week": week,
                    "formset": formset,
                    "zero_form": zero_form,
                    "show_zero_modal": True,
                    "num_preset_rows": num_preset_rows,
                    "day_labels": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                    "edits_allowed": edits_allowed,
                    "submission_deadline": week.period.submission_deadline,
                },
            )

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
                    new_initial, num_preset_rows = _build_initial_for_week(
                        profile, week
                    )
                    formset = WeeklyTimesheetLineFormSet(
                        initial=new_initial, prefix="lines"
                    )
                    return render(
                        request,
                        "timeeffort/weekly_entry.html",
                        {
                            "timesheet": timesheet,
                            "week": week,
                            "formset": formset,
                            "zero_form": zero_form,
                            "show_zero_modal": True,
                            "num_preset_rows": num_preset_rows,
                            "day_labels": [
                                "Sun",
                                "Mon",
                                "Tue",
                                "Wed",
                                "Thu",
                                "Fri",
                                "Sat",
                            ],
                        },
                    )
                timesheet.submit()
                _invalidate_period_report_pdf(profile, week.period)
                messages.success(
                    request, f"Week of {week.start_date} submitted successfully."
                )
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
        Activity.objects.filter(is_preset=True, is_active=True).order_by(
            "sort_order", "name"
        )
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
    for act_id, grant_code in carried_keys:
        key = (act_id, grant_code)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        line = existing_lines.get(key)
        initial.append(
            _line_to_initial(line)
            if line
            else {
                "activity": act_id,
                "grant_code": grant_code,
                "hours_sun": Decimal("0"),
                "hours_mon": Decimal("0"),
                "hours_tue": Decimal("0"),
                "hours_wed": Decimal("0"),
                "hours_thu": Decimal("0"),
                "hours_fri": Decimal("0"),
                "hours_sat": Decimal("0"),
                "description": "",
            }
        )

    # 3. Any custom rows saved this week that weren't in carry-forward
    for key, line in existing_lines.items():
        if key not in seen_keys:
            initial.append(_line_to_initial(line))

    return initial, num_preset_rows


# =============================================================================
# SALARY WEEKLY ENTRY HELPERS
# =============================================================================


def _find_carry_forward_week(profile, week):
    """Return the best source week to carry forward from for salary entry.

    - week_number > 1: previous week in same period
    - week_number == 1: week 2 of previous period (works across 28-day boundary too)
    """
    if week.week_number > 1:
        return ReportingWeek.objects.filter(
            period=week.period, week_number=week.week_number - 1
        ).first()
    # week_number == 1 → go to previous period's week 2
    try:
        prev_period = ReportingPeriod.objects.get(
            calendar=week.period.calendar,
            period_index=week.period.period_index - 1,
        )
        return ReportingWeek.objects.filter(period=prev_period, week_number=2).first()
    except ReportingPeriod.DoesNotExist:
        return None


def _build_salary_rows(profile, week):
    """
    Build pre-populated row data for the salary weekly entry form.

    Priority: existing lines for this week → carry-forward from prior week → defaults.
    Custom lines are placed in 2 fixed slots.

    Returns (direct_rows, indirect_rows, custom_rows).
    """
    holiday_activity_ids = set(
        Activity.objects.filter(is_holiday_activity=True).values_list("id", flat=True)
    )
    holiday_dates = set(
        AIMHoliday.objects.filter(
            date__range=[week.start_date, week.end_date]
        ).values_list("date", flat=True)
    )
    day_dates = {
        d: week.start_date + timedelta(days=i)
        for i, d in enumerate(SALARY_DAY_KEYS)
    }

    # Existing timesheet lines for this week (if any)
    existing_ts = WeeklyTimesheet.objects.filter(staff=profile, week=week).first()
    existing_by_act = {}
    existing_custom = []
    has_existing_lines = False
    if existing_ts:
        lines_qs = list(existing_ts.lines.select_related("activity").all())
        has_existing_lines = bool(lines_qs)
        for line in lines_qs:
            if line.activity_id:
                existing_by_act[line.activity_id] = line
            else:
                existing_custom.append(line)

    # Carry-forward source: only used when no lines have been saved yet for this week
    cf_by_act = {}
    cf_custom = []
    if not has_existing_lines:
        cf_week = _find_carry_forward_week(profile, week)
        if cf_week:
            cf_ts = WeeklyTimesheet.objects.filter(staff=profile, week=cf_week).first()
            if cf_ts:
                for line in cf_ts.lines.select_related("activity").all():
                    if line.activity_id in holiday_activity_ids:
                        continue
                    if line.activity_id:
                        act = line.activity
                        if act.valid_to and act.valid_to < week.start_date:
                            continue
                        cf_by_act[line.activity_id] = line
                    else:
                        cf_custom.append(line)

    try:
        salary_indirect = profile.salary_indirect
    except Exception:
        salary_indirect = None

    def _get_hours(line, zero_holidays=False):
        h = {}
        for d in SALARY_DAY_KEYS:
            val = getattr(line, f"hours_{d}") or Decimal("0")
            if zero_holidays and day_dates[d] in holiday_dates:
                val = Decimal("0")
            h[d] = val
        return h

    def _zero_hours():
        return {d: Decimal("0") for d in SALARY_DAY_KEYS}

    def _pairs(h):
        """Convert hours dict to list of (day_key, value) pairs for template iteration."""
        return [(d, h[d]) for d in SALARY_DAY_KEYS]

    # --- Direct activity rows ---
    direct_activities = list(
        Activity.objects.filter(
            is_active=True,
            classification=Activity.Classification.DIRECT,
        ).exclude(id__in=holiday_activity_ids).order_by("sort_order", "name")
    )
    direct_rows = []
    for act in direct_activities:
        if not act.is_valid_for_week(week.start_date, week.end_date):
            continue
        if act.id in existing_by_act:
            line = existing_by_act[act.id]
            hours = _get_hours(line)
            grant = line.grant_code
        elif act.id in cf_by_act:
            line = cf_by_act[act.id]
            hours = _get_hours(line, zero_holidays=True)
            grant = line.grant_code
        else:
            hours = _zero_hours()
            grant = act.default_grant_code
        direct_rows.append({"activity": act, "grant_code": grant, "hours_pairs": _pairs(hours)})

    # --- Indirect / leave / unallowable rows ---
    # Map activity name → SalaryIndirectAllocation field for default pre-fill
    _indirect_default_map = {
        name: field for name, _cls, field in SALARY_INDIRECT_SLOTS
    }

    indirect_activities = list(
        Activity.objects.filter(
            is_active=True,
            classification__in=[
                Activity.Classification.INDIRECT,
                Activity.Classification.LEAVE,
                Activity.Classification.UNALLOWABLE,
            ],
        ).order_by("sort_order", "name")
    )

    indirect_rows = []

    # Holiday activity: shown first in indirect section, auto-filled with 8h per holiday day
    if holiday_dates:
        try:
            holiday_act = Activity.objects.get(is_holiday_activity=True, is_active=True)
            if holiday_act.id in existing_by_act:
                hours = _get_hours(existing_by_act[holiday_act.id])
            else:
                hours = _zero_hours()
                for d in SALARY_DAY_KEYS:
                    if day_dates[d] in holiday_dates:
                        hours[d] = Decimal("8")
            indirect_rows.append({"activity": holiday_act, "hours_pairs": _pairs(hours)})
            holiday_activity_ids.add(holiday_act.id)  # exclude from regular loop below
        except Activity.DoesNotExist:
            pass

    for act in indirect_activities:
        if act.id in holiday_activity_ids:
            continue
        if act.id in existing_by_act:
            line = existing_by_act[act.id]
            hours = _get_hours(line)
        elif act.id in cf_by_act:
            line = cf_by_act[act.id]
            hours = _get_hours(line, zero_holidays=True)
        else:
            default_field = _indirect_default_map.get(act.name)
            default_weekly = (
                getattr(salary_indirect, default_field, Decimal("0"))
                if salary_indirect and default_field else Decimal("0")
            )
            hours = _zero_hours()
            if default_weekly > 0:
                per_day = (default_weekly / 5).quantize(Decimal("0.25"))
                for d in ["mon", "tue", "wed", "thu", "fri"]:
                    if day_dates[d] not in holiday_dates:
                        hours[d] = per_day
        indirect_rows.append({"activity": act, "hours_pairs": _pairs(hours)})

    # --- Custom slots (2 fixed) ---
    custom_rows = []
    for slot_idx, slot_num in enumerate([1, 2]):
        if slot_idx < len(existing_custom):
            line = existing_custom[slot_idx]
            custom_rows.append({
                "slot": slot_num,
                "name": line.custom_activity_name,
                "grant_code": line.grant_code,
                "hours_pairs": _pairs(_get_hours(line)),
            })
        elif slot_idx < len(cf_custom):
            line = cf_custom[slot_idx]
            custom_rows.append({
                "slot": slot_num,
                "name": line.custom_activity_name,
                "grant_code": line.grant_code,
                "hours_pairs": _pairs(_get_hours(line, zero_holidays=True)),
            })
        else:
            custom_rows.append({
                "slot": slot_num,
                "name": "",
                "grant_code": "",
                "hours_pairs": _pairs(_zero_hours()),
            })

    return direct_rows, indirect_rows, custom_rows


def _save_salary_lines_from_post(post_data, timesheet):
    """
    Parse POST data from the salary weekly entry form and persist lines.
    Replaces all existing lines. Resets status to DRAFT.
    """
    timesheet.lines.all().delete()

    all_activities = Activity.objects.filter(is_active=True)

    for act in all_activities:
        prefix = f"act_{act.id}_"
        if not any(f"{prefix}{d}" in post_data for d in SALARY_DAY_KEYS):
            continue  # activity wasn't on this form
        grant_code = post_data.get(f"{prefix}grant", act.default_grant_code or "")
        hours = {}
        for d in SALARY_DAY_KEYS:
            val = post_data.get(f"{prefix}{d}", "").strip()
            try:
                hours[f"hours_{d}"] = Decimal(val) if val else Decimal("0")
            except Exception:
                hours[f"hours_{d}"] = Decimal("0")
        WeeklyTimesheetLine.objects.create(
            timesheet=timesheet,
            activity=act,
            grant_code=grant_code,
            **hours,
        )

    for slot in [1, 2]:
        name = post_data.get(f"custom_{slot}_name", "").strip()
        grant_code = post_data.get(f"custom_{slot}_grant", "").strip()
        hours = {}
        has_hours = False
        for d in SALARY_DAY_KEYS:
            val = post_data.get(f"custom_{slot}_{d}", "").strip()
            try:
                h = Decimal(val) if val else Decimal("0")
            except Exception:
                h = Decimal("0")
            hours[f"hours_{d}"] = h
            if h > 0:
                has_hours = True
        if name or has_hours:
            WeeklyTimesheetLine.objects.create(
                timesheet=timesheet,
                activity=None,
                custom_activity_name=name,
                grant_code=grant_code,
                **hours,
            )

    if timesheet.status == WeeklyTimesheet.Status.SUBMITTED:
        timesheet.status = WeeklyTimesheet.Status.DRAFT
        timesheet.save(update_fields=["status", "updated_at"])


def _salary_weekly_entry(request, profile, week):
    """Salary staff weekly entry: pre-listed activities, never locked after submission."""
    timesheet, _ = WeeklyTimesheet.objects.get_or_create(
        staff=profile,
        week=week,
        defaults={"status": WeeklyTimesheet.Status.DRAFT},
    )
    holiday_dates = set(
        AIMHoliday.objects.filter(
            date__range=[week.start_date, week.end_date]
        ).values_list("date", flat=True)
    )

    if request.method == "POST":
        action = request.POST.get("action", "save")

        if action == "confirm_zero":
            zero_form = ZeroWeekConfirmForm(request.POST)
            if zero_form.is_valid():
                _save_salary_lines_from_post(request.POST, timesheet)
                timesheet.zero_week_reason = zero_form.cleaned_data["zero_week_reason"]
                timesheet.submit()
                _invalidate_period_report_pdf(profile, week.period)
                messages.success(
                    request,
                    f"Week of {week.start_date} confirmed as zero-hour and submitted.",
                )
                return redirect("timeeffort:dashboard")
            direct_rows, indirect_rows, custom_rows = _build_salary_rows(profile, week)
            return render(
                request,
                "timeeffort/weekly_entry_salary.html",
                {
                    "timesheet": timesheet,
                    "week": week,
                    "profile": profile,
                    "direct_rows": direct_rows,
                    "indirect_rows": indirect_rows,
                    "custom_rows": custom_rows,
                    "zero_form": zero_form,
                    "show_zero_modal": True,
                    "day_labels": SALARY_DAY_LABELS,
                    "day_keys": SALARY_DAY_KEYS,
                    "holiday_dates": holiday_dates,
                },
            )

        _save_salary_lines_from_post(request.POST, timesheet)

        if action == "submit":
            total = timesheet.total_hours
            if total == 0:
                zero_form = ZeroWeekConfirmForm()
                direct_rows, indirect_rows, custom_rows = _build_salary_rows(profile, week)
                return render(
                    request,
                    "timeeffort/weekly_entry_salary.html",
                    {
                        "timesheet": timesheet,
                        "week": week,
                        "profile": profile,
                        "direct_rows": direct_rows,
                        "indirect_rows": indirect_rows,
                        "custom_rows": custom_rows,
                        "zero_form": zero_form,
                        "show_zero_modal": True,
                        "day_labels": SALARY_DAY_LABELS,
                        "day_keys": SALARY_DAY_KEYS,
                        "holiday_dates": holiday_dates,
                    },
                )
            timesheet.submit()
            _invalidate_period_report_pdf(profile, week.period)
            messages.success(request, f"Week of {week.start_date} submitted.")
            return redirect("timeeffort:dashboard")

        messages.success(request, "Draft saved.")
        return redirect("timeeffort:weekly_entry", week_id=week.id)

    # GET
    direct_rows, indirect_rows, custom_rows = _build_salary_rows(profile, week)
    zero_form = ZeroWeekConfirmForm()
    return render(
        request,
        "timeeffort/weekly_entry_salary.html",
        {
            "timesheet": timesheet,
            "week": week,
            "profile": profile,
            "direct_rows": direct_rows,
            "indirect_rows": indirect_rows,
            "custom_rows": custom_rows,
            "zero_form": zero_form,
            "show_zero_modal": False,
            "day_labels": SALARY_DAY_LABELS,
            "day_keys": SALARY_DAY_KEYS,
            "holiday_dates": holiday_dates,
        },
    )


@login_required
@require_POST
def copy_previous_period(request, period_id):
    """Copy all 4 weeks from the previous 28-day salary window into the current window."""
    profile = _get_staff_profile(request)
    if not profile or not profile.is_salary:
        raise Http404

    period = get_object_or_404(ReportingPeriod, pk=period_id)
    # Ensure we have the anchor (even period_index)
    if not period.is_salary_month_start:
        try:
            period = ReportingPeriod.objects.get(
                calendar=period.calendar, period_index=period.period_index - 1
            )
        except ReportingPeriod.DoesNotExist:
            messages.error(request, "Could not find anchor period.")
            return redirect("timeeffort:dashboard")

    prev_anchor_idx = period.period_index - 2
    try:
        prev_anchor = ReportingPeriod.objects.get(
            calendar=period.calendar, period_index=prev_anchor_idx
        )
    except ReportingPeriod.DoesNotExist:
        messages.error(request, "No previous period found to copy from.")
        return redirect("timeeffort:dashboard")

    prev_weeks = list(
        ReportingWeek.objects.filter(period__in=_get_salary_periods(prev_anchor)).order_by("start_date")
    )
    curr_weeks = list(
        ReportingWeek.objects.filter(period__in=_get_salary_periods(period)).order_by("start_date")
    )

    if len(prev_weeks) != len(curr_weeks):
        messages.error(request, "Week count mismatch between periods.")
        return redirect("timeeffort:dashboard")

    holiday_activity_ids = set(
        Activity.objects.filter(is_holiday_activity=True).values_list("id", flat=True)
    )

    copied = 0
    for prev_week, curr_week in zip(prev_weeks, curr_weeks):
        prev_ts = WeeklyTimesheet.objects.filter(staff=profile, week=prev_week).first()
        if not prev_ts:
            continue

        curr_ts, _ = WeeklyTimesheet.objects.get_or_create(
            staff=profile,
            week=curr_week,
            defaults={"status": WeeklyTimesheet.Status.DRAFT},
        )

        holiday_dates_curr = set(
            AIMHoliday.objects.filter(
                date__range=[curr_week.start_date, curr_week.end_date]
            ).values_list("date", flat=True)
        )
        day_dates = {
            d: curr_week.start_date + timedelta(days=i)
            for i, d in enumerate(SALARY_DAY_KEYS)
        }

        curr_ts.lines.all().delete()
        for line in prev_ts.lines.select_related("activity").all():
            if line.activity_id and line.activity_id in holiday_activity_ids:
                continue
            if line.activity and line.activity.valid_to and line.activity.valid_to < curr_week.start_date:
                continue
            hours = {}
            for d in SALARY_DAY_KEYS:
                val = getattr(line, f"hours_{d}") or Decimal("0")
                if day_dates[d] in holiday_dates_curr:
                    val = Decimal("0")
                hours[f"hours_{d}"] = val
            WeeklyTimesheetLine.objects.create(
                timesheet=curr_ts,
                activity_id=line.activity_id,
                custom_activity_name=line.custom_activity_name,
                grant_code=line.grant_code,
                **hours,
            )

        if curr_ts.status == WeeklyTimesheet.Status.SUBMITTED:
            curr_ts.status = WeeklyTimesheet.Status.DRAFT
            curr_ts.save(update_fields=["status", "updated_at"])

        copied += 1

    _invalidate_period_report_pdf(profile, period)
    messages.success(request, f"Copied {copied} week(s) from previous period.")
    return redirect("timeeffort:dashboard")


# =============================================================================
# PERIOD SUMMARY
# =============================================================================


@login_required
def period_summary(request, period_id):
    profile = _get_staff_profile(request)
    if not profile:
        raise Http404

    period = get_object_or_404(ReportingPeriod, pk=period_id)

    if profile.is_salary:
        all_periods = _get_salary_periods(period)
        weeks = ReportingWeek.objects.filter(period__in=all_periods).order_by("start_date")
        # Ensure we always use the anchor (salary-month-start) period for the report lookup
        anchor_period = all_periods.filter(
            period_index=period.period_index if period.period_index % 2 == 0 else period.period_index - 1
        ).first() or period
        period_end = _get_28day_end(anchor_period)
        period_label = anchor_period.salary_month_label
    else:
        weeks = period.weeks.all()
        anchor_period = period
        period_end = period.end_date
        period_label = period.label

    week_statuses = []
    for week in weeks:
        ts = WeeklyTimesheet.objects.filter(staff=profile, week=week).first()
        week_statuses.append({"week": week, "timesheet": ts})

    all_submitted = bool(week_statuses) and all(
        ws["timesheet"] and ws["timesheet"].status == WeeklyTimesheet.Status.SUBMITTED
        for ws in week_statuses
    )

    report = PeriodReport.objects.filter(staff=profile, period=anchor_period).first()
    latest_pdf = None
    if report:
        latest_pdf = (
            report.pdfs.filter(pdf_type=PDFSnapshot.PDFType.FINAL)
            .order_by("-version")
            .first()
        )

    return render(
        request,
        "timeeffort/period_summary.html",
        {
            "period": anchor_period,
            "period_end": period_end,
            "period_label": period_label,
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

    # Check weeks directly — PeriodReport may not exist yet on first visit.
    # Salary staff span two 14-day periods (28-day window); check all 4 weeks.
    if profile.is_salary:
        period_weeks = ReportingWeek.objects.filter(period__in=_get_salary_periods(period))
    else:
        period_weeks = period.weeks.all()
    submitted_count = WeeklyTimesheet.objects.filter(
        staff=profile,
        week__in=period_weeks,
        status=WeeklyTimesheet.Status.SUBMITTED,
    ).count()

    if submitted_count < period_weeks.count():
        messages.error(
            request, "All weeks must be submitted before generating the final report."
        )
        return redirect("timeeffort:period_summary", period_id=period_id)

    # Get or initialize the period report
    report, _ = PeriodReport.objects.get_or_create(
        staff=profile,
        period=period,
        defaults={"submission_type": PeriodReport.SubmissionType.HOURS},
    )
    if report.status == PeriodReport.Status.DRAFT:
        report = initialize_period_report(report)
        _copy_prior_duties_descriptions(profile, report)

    DescribeFormSet = modelformset_factory(
        PeriodReportLine,
        form=PeriodDescribeForm,
        extra=0,
    )

    if request.method == "POST":
        formset = DescribeFormSet(
            request.POST, queryset=report.lines.order_by("sort_order")
        )
        if formset.is_valid():
            formset.save()
            report.refresh_from_db()
            # Validate percentages before allowing generation
            lines = report.lines.all()
            rows = [{"percentage": l.percentage} for l in lines]
            if not validate_period_percentages(
                [{"percentage": l.percentage} for l in lines]
            ):
                messages.error(
                    request,
                    f"Percentages do not sum to 100% (got "
                    f"{sum(l.percentage for l in lines):.2f}%). Contact an admin.",
                )
                return redirect("timeeffort:final_report_describe", period_id=period_id)

            from .services import generate_final_pdf

            generate_final_pdf(report, generated_by=request.user)
            messages.success(
                request, "Final report generated. You can now download your PDF."
            )
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
        messages.error(
            request, "Weekly report can only be downloaded after submission."
        )
        return redirect("timeeffort:weekly_entry", week_id=timesheet.week_id)

    snapshot = (
        timesheet.pdfs.filter(pdf_type=PDFSnapshot.PDFType.WEEKLY)
        .order_by("-version")
        .first()
    )
    if not snapshot:
        snapshot = generate_weekly_pdf(timesheet, generated_by=request.user)

    return _serve_pdf(snapshot, f"weekly_report_{timesheet.week.start_date}.pdf")


@login_required
def download_final_pdf(request, report_id):
    profile = _get_staff_profile(request)
    if not profile:
        raise Http404

    report = get_object_or_404(PeriodReport, pk=report_id, staff=profile)
    snapshot = (
        report.pdfs.filter(pdf_type=PDFSnapshot.PDFType.FINAL)
        .order_by("-version")
        .first()
    )

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


def _get_28day_end(period):
    """Return the end date of the 28-day window starting at period (even period_index)."""
    try:
        next_p = ReportingPeriod.objects.get(
            calendar=period.calendar,
            period_index=period.period_index + 1,
        )
        return next_p.end_date
    except ReportingPeriod.DoesNotExist:
        return period.end_date


def _get_salary_periods(period):
    """Return the two ReportingPeriods that form the 28-day salary window containing period."""
    anchor_idx = period.period_index if period.period_index % 2 == 0 else period.period_index - 1
    return ReportingPeriod.objects.filter(
        calendar=period.calendar,
        period_index__in=[anchor_idx, anchor_idx + 1],
    ).order_by("period_index")


def _copy_prior_duties_descriptions(profile, report):
    """Pre-fill duties_description on new report lines from the most recent prior period report."""
    prior = (
        PeriodReport.objects.filter(
            staff=profile,
            period__start_date__lt=report.period.start_date,
            status__in=[
                PeriodReport.Status.SUBMITTED,
                PeriodReport.Status.SUPERVISOR_APPROVED,
                PeriodReport.Status.PROCESSED,
            ],
        )
        .order_by("-period__start_date")
        .first()
    )
    if not prior:
        return
    desc_map = {
        ln.activity_name_snapshot: ln.duties_description
        for ln in prior.lines.all()
        if ln.duties_description
    }
    for line in report.lines.all():
        desc = desc_map.get(line.activity_name_snapshot, "")
        if desc and not line.duties_description:
            line.duties_description = desc
            line.save(update_fields=["duties_description"])


def _salary_dashboard(request, profile):
    """Salary dashboard: groups periods into 28-day windows, shows all 4 weekly slots each."""
    available_years, selected_year = _get_year_filter(request)

    candidates = list(
        ReportingPeriod.objects.filter(start_date__year=selected_year).order_by("-start_date")
    )
    active_pairs = [p for p in candidates if p.is_salary_month_start]

    period_summaries = []
    for period in active_pairs:
        end_date = _get_28day_end(period)
        all_periods = _get_salary_periods(period)
        all_weeks = ReportingWeek.objects.filter(period__in=all_periods).order_by("start_date")

        submitted_ids = set(
            WeeklyTimesheet.objects.filter(
                staff=profile,
                week__in=all_weeks,
                status=WeeklyTimesheet.Status.SUBMITTED,
            ).values_list("week_id", flat=True)
        )
        outstanding = all_weeks.exclude(id__in=submitted_ids)
        report = PeriodReport.objects.filter(staff=profile, period=period).first()

        week_statuses = []
        for week in all_weeks:
            ts = WeeklyTimesheet.objects.filter(staff=profile, week=week).first()
            week_statuses.append({"week": week, "timesheet": ts})

        has_prev = ReportingPeriod.objects.filter(
            calendar=period.calendar,
            period_index=period.period_index - 2,
        ).exists()
        holiday_count = AIMHoliday.objects.filter(
            date__range=[period.start_date, end_date]
        ).count()
        period_summaries.append({
            "period": period,
            "period_label": period.salary_month_label,
            "period_end": end_date,
            "total_weeks": all_weeks.count(),
            "submitted_count": len(submitted_ids),
            "outstanding_weeks": outstanding,
            "week_statuses": week_statuses,
            "report": report,
            "has_prev": has_prev,
            "holiday_count": holiday_count,
        })

    # Sort: upcoming deadline first, past-unsubmitted second, fully-submitted last
    today = timezone.now().date()

    def _sort_key(s):
        rpt = s["report"]
        if rpt and rpt.status not in (None, PeriodReport.Status.DRAFT):
            return (2, 0)
        deadline = s["period"].submission_deadline
        if deadline:
            delta = (deadline.date() - today).days
            return (0, delta) if delta >= 0 else (1, -delta)
        return (1, 99999)

    period_summaries.sort(key=_sort_key)

    recent_reports = (
        PeriodReport.objects.filter(
            staff=profile,
            status__in=[
                PeriodReport.Status.SUBMITTED,
                PeriodReport.Status.SUPERVISOR_APPROVED,
                PeriodReport.Status.PROCESSED,
            ],
        )
        .select_related("period")
        .order_by("-period__start_date")[:5]
    )

    return render(
        request,
        "timeeffort/dashboard.html",
        {
            "profile": profile,
            "period_summaries": period_summaries,
            "is_salary": True,
            "recent_reports": recent_reports,
            "available_years": available_years,
            "selected_year": selected_year,
        },
    )


def _invalidate_period_report_pdf(profile, period):
    """Clear the generated final PDF for the PeriodReport covering this period.

    Called after a weekly timesheet is re-submitted so the next download triggers
    a fresh rollup and PDF regeneration.
    """
    if not profile.is_hourly:
        anchor_idx = period.period_index if period.period_index % 2 == 0 else period.period_index - 1
        try:
            anchor_period = ReportingPeriod.objects.get(
                calendar=period.calendar, period_index=anchor_idx
            )
        except ReportingPeriod.DoesNotExist:
            return
    else:
        anchor_period = period

    report = PeriodReport.objects.filter(staff=profile, period=anchor_period).first()
    if report and report.generated_at is not None:
        report.pdfs.filter(pdf_type=PDFSnapshot.PDFType.FINAL).delete()
        report.generated_at = None
        report.save(update_fields=["generated_at", "updated_at"])


def _director_dashboard(request, profile):
    """Director dashboard: shows 28-day period pairs only (no weekly timesheets)."""
    available_years, selected_year = _get_year_filter(request)

    candidates = list(
        ReportingPeriod.objects.filter(start_date__year=selected_year).order_by(
            "-start_date"
        )
    )
    # Only even period_index periods (start of 28-day salary month)
    active_pairs = [p for p in candidates if p.is_salary_month_start]

    period_summaries = []
    for period in active_pairs:
        report = PeriodReport.objects.filter(staff=profile, period=period).first()
        end_date = _get_28day_end(period)
        holiday_count = AIMHoliday.objects.filter(
            date__range=[period.start_date, end_date]
        ).count()
        period_summaries.append(
            {
                "period": period,
                "period_label": period.salary_month_label,
                "period_end": end_date,
                "report": report,
                "holiday_count": holiday_count,
                "holiday_pct": holiday_count * 5,
            }
        )

    has_defaults = DirectorDefaultAllocation.objects.filter(profile=profile).exists()
    recent_reports = (
        PeriodReport.objects.filter(
            staff=profile,
            status__in=[
                PeriodReport.Status.SUBMITTED,
                PeriodReport.Status.SUPERVISOR_APPROVED,
                PeriodReport.Status.PROCESSED,
            ],
        )
        .select_related("period")
        .order_by("-period__start_date")[:5]
    )

    return render(
        request,
        "timeeffort/dashboard.html",
        {
            "profile": profile,
            "period_summaries": period_summaries,
            "is_director": True,
            "has_defaults": has_defaults,
            "recent_reports": recent_reports,
            "available_years": available_years,
            "selected_year": selected_year,
        },
    )


@login_required
def director_period_entry(request, period_id):
    profile = _get_staff_profile(request)
    if not profile or not profile.is_director:
        raise Http404

    period = get_object_or_404(ReportingPeriod, pk=period_id)

    if not period.is_salary_month_start:
        messages.error(request, "Invalid period for a director report.")
        return redirect("timeeffort:dashboard")

    if period.is_locked:
        messages.error(request, "This reporting period is locked.")
        return redirect("timeeffort:dashboard")

    end_date = _get_28day_end(period)
    holiday_count = AIMHoliday.objects.filter(
        date__range=[period.start_date, end_date]
    ).count()
    holiday_pct = Decimal(str(holiday_count * 5))
    holidays = AIMHoliday.objects.filter(date__range=[period.start_date, end_date])

    report, _ = PeriodReport.objects.get_or_create(
        staff=profile,
        period=period,
        defaults={"submission_type": PeriodReport.SubmissionType.PCT},
    )

    edits_allowed = period.edits_allowed
    if report.status != PeriodReport.Status.DRAFT and not edits_allowed:
        return render(
            request,
            "timeeffort/director_entry_locked.html",
            {
                "report": report,
                "period": period,
            },
        )

    if request.method == "POST":
        action = request.POST.get("action", "save")
        form = DirectorPeriodEntryForm(request.POST, holiday_pct=holiday_pct)
        if form.is_valid():
            _save_director_report_lines(
                report, form.cleaned_data, holiday_pct, form.cleaned_data.get("main_grant_code", "")
            )
            if action == "submit":
                report.submit()
                messages.success(
                    request,
                    f"Effort report for {period.salary_month_label} submitted.",
                )
                return redirect("timeeffort:dashboard")
            messages.success(request, "Draft saved.")
            return redirect("timeeffort:director_period_entry", period_id=period.id)
    else:
        if report.lines.exists():
            initial = _report_lines_to_form_data(report)
        else:
            initialize_director_period_report(report, holiday_pct=holiday_pct)
            initial = _report_lines_to_form_data(report)
        form = DirectorPeriodEntryForm(initial=initial, holiday_pct=holiday_pct)

    return render(
        request,
        "timeeffort/director_period_entry.html",
        {
            "profile": profile,
            "period": period,
            "report": report,
            "end_date": end_date,
            "form": form,
            "holiday_count": holiday_count,
            "holiday_pct": holiday_pct,
            "holidays": holidays,
            "edits_allowed": edits_allowed,
            "submission_deadline": period.submission_deadline,
        },
    )


@login_required
def download_director_pdf(request, submission_id):
    """submission_id is a PeriodReport pk (name kept for URL compatibility)."""
    profile = _get_staff_profile(request)
    if not profile:
        raise Http404

    report = get_object_or_404(PeriodReport, pk=submission_id, staff=profile)

    if report.status == PeriodReport.Status.DRAFT:
        messages.error(
            request, "Director report can only be downloaded after submission."
        )
        return redirect("timeeffort:director_period_entry", period_id=report.period_id)

    snapshot = (
        report.pdfs.filter(pdf_type=PDFSnapshot.PDFType.FINAL)
        .order_by("-version")
        .first()
    )
    if not snapshot:
        from .services import generate_final_pdf

        snapshot = generate_final_pdf(report, generated_by=request.user)

    filename = (
        f"director_report_{report.period.start_date}_{report.period.end_date}.pdf"
    )
    return _serve_pdf(snapshot, filename)


# --- Director helpers ---


def _save_director_report_lines(report, cleaned, holiday_pct, main_grant_code=""):
    """Persist DirectorPeriodEntryForm data as PeriodReportLine objects."""
    from .models import Activity

    report.lines.all().delete()
    sort = 0

    main_pct = cleaned.get("main_grant_pct") or Decimal("0")
    PeriodReportLine.objects.create(
        period_report=report,
        activity_name_snapshot=f"Direct — {main_grant_code or 'Main Grant'}",
        grant_code_snapshot=main_grant_code,
        classification_snapshot=Activity.Classification.DIRECT,
        total_hours=None,
        percentage=main_pct,
        duties_description=cleaned.get("main_grant_desc", ""),
        sort_order=sort,
    )
    sort += 1

    for i in range(1, 5):
        code = cleaned.get(f"extra_grant_code_{i}", "")
        pct = cleaned.get(f"extra_grant_pct_{i}") or Decimal("0")
        if code or pct > 0:
            PeriodReportLine.objects.create(
                period_report=report,
                activity_name_snapshot=f"Direct — {code or f'Grant {i}'}",
                grant_code_snapshot=code,
                classification_snapshot=Activity.Classification.DIRECT,
                total_hours=None,
                percentage=pct,
                duties_description=cleaned.get(f"extra_grant_desc_{i}", ""),
                sort_order=sort,
            )
            sort += 1

    indirect_rows = [
        (
            "Administrative",
            "pct_administrative",
            "desc_administrative",
            Activity.Classification.INDIRECT,
        ),
        (
            "Other Activity",
            "pct_other_activity",
            "desc_other_activity",
            Activity.Classification.INDIRECT,
        ),
        (
            "Sick / Personal Day",
            "pct_sick_personal",
            "desc_sick_personal",
            Activity.Classification.LEAVE,
        ),
        ("Vacation", "pct_vacation", "desc_vacation", Activity.Classification.LEAVE),
        (
            "Fundraising / PR",
            "pct_fundraising_pr",
            "desc_fundraising_pr",
            Activity.Classification.UNALLOWABLE,
        ),
        (
            "Other Unallowable",
            "pct_other_unallowable",
            "desc_other_unallowable",
            Activity.Classification.UNALLOWABLE,
        ),
    ]
    for label, pct_field, desc_field, classification in indirect_rows:
        pct = cleaned.get(pct_field) or Decimal("0")
        if pct > 0:
            PeriodReportLine.objects.create(
                period_report=report,
                activity_name_snapshot=label,
                grant_code_snapshot="",
                classification_snapshot=classification,
                total_hours=None,
                percentage=pct,
                duties_description=cleaned.get(desc_field, ""),
                sort_order=sort,
            )
            sort += 1


def _report_lines_to_form_data(report):
    """Read PeriodReportLine objects back into DirectorPeriodEntryForm initial data."""
    from .models import Activity

    data = {}
    extra_idx = 1
    for line in report.lines.order_by("sort_order"):
        if line.classification_snapshot == Activity.Classification.DIRECT:
            if "main_grant_pct" not in data:
                data["main_grant_code"] = line.grant_code_snapshot
                data["main_grant_pct"] = line.percentage
                data["main_grant_desc"] = line.duties_description
            elif extra_idx <= 4:
                data[f"extra_grant_code_{extra_idx}"] = line.grant_code_snapshot
                data[f"extra_grant_pct_{extra_idx}"] = line.percentage
                data[f"extra_grant_desc_{extra_idx}"] = line.duties_description
                extra_idx += 1
        elif line.activity_name_snapshot == "Employer Holiday":
            pass  # auto-calculated, not editable in the form
        else:
            label_map = {
                "Administrative": ("pct_administrative", "desc_administrative"),
                "Other Activity": ("pct_other_activity", "desc_other_activity"),
                "Sick / Personal Day": ("pct_sick_personal", "desc_sick_personal"),
                "Vacation": ("pct_vacation", "desc_vacation"),
                "Fundraising / PR": ("pct_fundraising_pr", "desc_fundraising_pr"),
                "Other Unallowable": (
                    "pct_other_unallowable",
                    "desc_other_unallowable",
                ),
            }
            if line.activity_name_snapshot in label_map:
                pct_f, desc_f = label_map[line.activity_name_snapshot]
                data[pct_f] = line.percentage
                data[desc_f] = line.duties_description
    return data


@login_required
def director_set_defaults(request):
    profile = _get_staff_profile(request)
    if not profile or profile.staff_type != StaffTimesheetProfile.StaffType.DIRECTOR:
        raise Http404

    defaults, _ = DirectorDefaultAllocation.objects.get_or_create(profile=profile)

    if request.method == "POST":
        form = DirectorDefaultsForm(request.POST, instance=defaults)
        if form.is_valid():
            form.save()
            messages.success(request, "Default allocations saved.")
            return redirect("timeeffort:dashboard")
    else:
        form = DirectorDefaultsForm(instance=defaults)

    return render(
        request,
        "timeeffort/director_defaults.html",
        {
            "profile": profile,
            "form": form,
        },
    )


# --- Director helpers ---


def _defaults_to_form_data(profile, holiday_pct):
    try:
        d = profile.director_defaults
        data = {
            "main_grant_code": d.main_grant_code,
            "main_grant_pct": d.main_grant_pct,
            "pct_administrative": max(Decimal("0"), d.pct_administrative - holiday_pct),
            "pct_other_activity": d.pct_other_activity,
            "pct_sick_personal": d.pct_sick_personal,
            "pct_vacation": d.pct_vacation,
            "pct_fundraising_pr": d.pct_fundraising_pr,
            "pct_other_unallowable": d.pct_other_unallowable,
        }
        for i in range(1, 5):
            data[f"extra_grant_code_{i}"] = getattr(d, f"extra_grant_code_{i}", "")
            data[f"extra_grant_pct_{i}"] = getattr(
                d, f"extra_grant_pct_{i}", Decimal("0")
            )
        return data
    except DirectorDefaultAllocation.DoesNotExist:
        return {}
