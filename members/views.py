import csv
from datetime import date, timedelta

from django.contrib import messages
from core.permissions import permission_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .birthdays import birthdays_in_week
from .followups import ABSENT_SERVICES, absentees, recent_visitors
from .forms import HouseholdForm, MemberForm
from .models import Household, Member

PAGE_SIZE = 25


def search_members(qs, query):
    for term in query.split():
        qs = qs.filter(
            Q(first_name__icontains=term)
            | Q(last_name__icontains=term)
            | Q(middle_name__icontains=term)
            | Q(nickname__icontains=term)
            | Q(phone__icontains=term)
            | Q(email__icontains=term)
        )
    return qs


def filtered_members(request):
    qs = Member.objects.select_related("household")
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    if query:
        qs = search_members(qs, query)
    if status == "active":
        qs = qs.filter(status__in=Member.ACTIVE_STATUSES)
    elif status in Member.Status.values:
        qs = qs.filter(status=status)
    return qs, query, status


@permission_required("members.view_member")
def member_list(request):
    qs, query, status = filtered_members(request)
    page = Paginator(qs, PAGE_SIZE).get_page(request.GET.get("page"))
    context = {
        "page": page,
        "query": query,
        "status": status,
        "status_choices": Member.Status.choices,
        "total": qs.count(),
    }
    # HTMX search/filter/paging only swaps the results table.
    template = "members/member_list.html#results" if request.htmx else "members/member_list.html"
    return render(request, template, context)


@permission_required("members.view_member")
def member_export(request):
    qs, _, _ = filtered_members(request)
    response = HttpResponse(content_type="text/csv")
    stamp = timezone.localdate().isoformat()
    response["Content-Disposition"] = f'attachment; filename="members-{stamp}.csv"'
    writer = csv.writer(response)
    writer.writerow([
        "Last name", "First name", "Middle name", "Suffix", "Status", "Gender", "Birth date",
        "Age", "Mobile", "Email", "Address", "Household", "Baptized", "Membership date",
    ])
    for m in qs:
        writer.writerow([
            m.last_name, m.first_name, m.middle_name, m.suffix, m.get_status_display(),
            m.get_gender_display(), m.birth_date or "", m.age if m.age is not None else "",
            m.phone, m.email, m.display_address, m.household or "",
            "Yes" if m.is_baptized else "No", m.membership_date or "",
        ])
    return response


@permission_required("members.view_member")
def member_detail(request, pk):
    member = get_object_or_404(Member.objects.select_related("household"), pk=pk)
    attendances = member.attendances.select_related("service__service_type").order_by("-service__date")

    # Attendance rate over the last 90 days, for the service types this member attends.
    from attendance.models import Service

    since = timezone.localdate() - timedelta(days=90)
    attended_types = member.attendances.values_list("service__service_type", flat=True).distinct()
    held = Service.objects.filter(date__gte=since, service_type__in=attended_types).count()
    attended = member.attendances.filter(service__date__gte=since).count()
    rate = round(attended / held * 100) if held else None

    context = {
        "member": member,
        "recent_attendance": attendances[:15],
        "attendance_total": attendances.count(),
        "rate_90": rate,
        "attended_90": attended,
        "held_90": held,
        "household_members": member.household.members.exclude(pk=member.pk) if member.household else [],
    }
    return render(request, "members/member_detail.html", context)


@permission_required("members.add_member")
def member_create(request):
    initial = {}
    if household_id := request.GET.get("household"):
        household = Household.objects.filter(pk=household_id).first()
        if household:
            initial["household"] = household
    form = MemberForm(request.POST or None, request.FILES or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        member = form.save()
        messages.success(request, f"{member.full_name} was added.")
        return redirect(member)
    return render(request, "members/member_form.html", {"form": form})


@permission_required("members.change_member")
def member_update(request, pk):
    member = get_object_or_404(Member, pk=pk)
    form = MemberForm(request.POST or None, request.FILES or None, instance=member)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"{member.full_name} was updated.")
        return redirect(member)
    return render(request, "members/member_form.html", {"form": form, "member": member})


@permission_required("members.delete_member")
@require_http_methods(["GET", "POST"])
def member_delete(request, pk):
    member = get_object_or_404(Member, pk=pk)
    if request.method == "POST":
        name = member.full_name
        member.delete()
        messages.success(request, f"{name} was deleted.")
        return redirect("members:member_list")
    return render(request, "members/member_confirm_delete.html", {"member": member})


@permission_required("members.view_member")
def birthdays(request):
    try:
        day = date.fromisoformat(request.GET.get("week", ""))
    except ValueError:
        day = timezone.localdate()
    start, end, people = birthdays_in_week(day)
    return render(request, "members/birthdays.html", {
        "start": start, "end": end, "people": people,
        "prev_week": start - timedelta(days=7), "next_week": start + timedelta(days=7),
        "is_this_week": start <= timezone.localdate() <= end,
    })


@permission_required("members.view_member")
def followups(request):
    absent, services = absentees()
    return render(request, "members/followups.html", {
        "visitors": recent_visitors(),
        "absentees": absent,
        "absent_services": services,
        "missed": ABSENT_SERVICES,
    })


@permission_required("members.view_household")
def household_list(request):
    query = request.GET.get("q", "").strip()
    qs = Household.objects.annotate(member_count=Count("members")).order_by("name")
    if query:
        qs = qs.filter(Q(name__icontains=query) | Q(members__last_name__icontains=query)).distinct()
    page = Paginator(qs, PAGE_SIZE).get_page(request.GET.get("page"))
    template = "members/household_list.html#results" if request.htmx else "members/household_list.html"
    return render(request, template, {"page": page, "query": query})


@permission_required("members.view_household")
def household_detail(request, pk):
    household = get_object_or_404(Household, pk=pk)
    return render(request, "members/household_detail.html", {
        "household": household,
        "members": household.members.all(),
    })


@permission_required("members.add_household")
def household_create(request):
    form = HouseholdForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        household = form.save()
        messages.success(request, f"{household.name} was added.")
        return redirect(household)
    return render(request, "members/household_form.html", {"form": form})


@permission_required("members.change_household")
def household_update(request, pk):
    household = get_object_or_404(Household, pk=pk)
    form = HouseholdForm(request.POST or None, instance=household)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"{household.name} was updated.")
        return redirect(household)
    return render(request, "members/household_form.html", {"form": form, "household": household})
