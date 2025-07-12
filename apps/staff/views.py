from django.shortcuts import render
from .models import StaffMember


def staff_list(request):
    staff = StaffMember.objects.filter(is_visible=True).order_by("order")
    return render(request, "staff/staff_list.html", {"staff": staff})
