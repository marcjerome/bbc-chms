from django.contrib import messages
from core.permissions import permission_required
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Count
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from members.forms import QuickVisitorForm
from members.models import Member
from members.views import search_members

from .forms import ServiceForm, ServiceTypeForm
from .models import Attendance, Service, ServiceType

SEARCH_LIMIT = 20


@permission_required("attendance.view_service")
def service_list(request):
    form = ServiceForm(request.POST or None)
    if request.method == "POST":
        if not request.user.has_perm("attendance.add_service"):
            messages.error(request, "You don't have permission to create services.")
            return redirect("attendance:service_list")
        if form.is_valid():
            service = form.save(commit=False)
            service.created_by = request.user
            service.save()
            return redirect(service)
    today = timezone.localdate()
    base = Service.objects.select_related("service_type").annotate(present=Count("attendances"))
    upcoming = base.filter(date__gt=today).order_by("date", "service_type__order")
    past = base.filter(date__lte=today).order_by("-date", "service_type__order")
    page = Paginator(past, 25).get_page(request.GET.get("page"))
    return render(request, "attendance/service_list.html", {
        "form": form, "page": page, "upcoming": upcoming, "today": today,
    })


@permission_required("attendance.change_service")
def service_update(request, pk):
    service = get_object_or_404(Service, pk=pk)
    form = ServiceForm(request.POST or None, instance=service)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"{service} was updated.")
        return redirect(service)
    return render(request, "attendance/service_form.html", {"form": form, "service": service})


@permission_required("attendance.view_servicetype")
def servicetype_list(request):
    types = ServiceType.objects.annotate(service_count=Count("services"))
    return render(request, "attendance/servicetype_list.html", {"types": types})


@permission_required("attendance.add_servicetype")
def servicetype_create(request):
    return _servicetype_form(request, ServiceType())


@permission_required("attendance.change_servicetype")
def servicetype_update(request, pk):
    return _servicetype_form(request, get_object_or_404(ServiceType, pk=pk))


def _servicetype_form(request, instance):
    form = ServiceTypeForm(request.POST or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"{form.instance.name} was saved.")
        return redirect("attendance:servicetype_list")
    return render(request, "attendance/servicetype_form.html", {"form": form, "servicetype": instance})


def expected_members():
    """People expected at services: members and regular attendees."""
    return Member.objects.filter(status__in=[Member.Status.MEMBER, Member.Status.ATTENDEE])


def checkin_context(service, query="", show_absent=False):
    """Context shared by the check-in page and its HTMX partials."""
    # member_id -> check-in time; also serves as the "is present" set in templates.
    present_ids = dict(service.attendances.values_list("member_id", "checked_in_at"))
    results = []
    if query:
        results = search_members(Member.objects.exclude(status=Member.Status.DECEASED), query)[:SEARCH_LIMIT]
    elif show_absent:
        results = expected_members().exclude(pk__in=present_ids).select_related("household")
    return {
        "service": service,
        "query": query,
        "show_absent": show_absent and not query,
        "absent_count": expected_members().exclude(pk__in=present_ids).count(),
        "results": results,
        "present_ids": present_ids,
        "present_count": len(present_ids),
        "registered_count": Member.objects.filter(status__in=Member.ACTIVE_STATUSES).count(),
        "checked_in": service.attendances.select_related("member"),
    }


@permission_required("attendance.view_attendance")
def service_checkin(request, pk):
    service = get_object_or_404(Service.objects.select_related("service_type"), pk=pk)
    query = request.GET.get("q", "").strip()
    context = checkin_context(service, query, show_absent=bool(request.GET.get("absent")))
    context["visitor_form"] = QuickVisitorForm()
    if request.htmx and request.htmx.target == "search-results":
        return render(request, "attendance/service_checkin.html#search_results", context)
    return render(request, "attendance/service_checkin.html", context)


def checkin_update(request, service, **extra):
    """
    HTMX response after any check-in change: counters, the checked-in list and (if given) the
    member's search row are swapped out-of-band; a visitor form, if given, is the main swap.
    """
    context = checkin_context(service)
    context.update(extra, oob=True)
    return render(request, "attendance/partials/checkin_update.html", context)


@permission_required("attendance.add_attendance")
@require_POST
def toggle_attendance(request, pk, member_id):
    service = get_object_or_404(Service, pk=pk)
    member = get_object_or_404(Member, pk=member_id)
    deleted, _ = Attendance.objects.filter(service=service, member=member).delete()
    if not deleted:
        try:
            Attendance.objects.create(service=service, member=member, recorded_by=request.user)
        except IntegrityError:
            pass  # double-tap race: already checked in
    return checkin_update(request, service, member=member)


@permission_required("attendance.view_attendance")
def service_live(request, pk):
    """Polled by the check-in page so QR self check-ins from the kiosk appear without reloading."""
    return checkin_update(request, get_object_or_404(Service, pk=pk))


@permission_required("attendance.change_service")
@require_POST
def adjust_guests(request, pk):
    service = get_object_or_404(Service, pk=pk)
    try:
        delta = int(request.POST.get("delta", 0))
    except ValueError:
        delta = 0
    service.guest_headcount = max(0, service.guest_headcount + delta)
    service.save(update_fields=["guest_headcount"])
    return checkin_update(request, service)


@permission_required("attendance.add_attendance")
@require_POST
def add_visitor(request, pk):
    service = get_object_or_404(Service, pk=pk)
    form = QuickVisitorForm(request.POST)
    if form.is_valid():
        member = form.save(commit=False)
        member.status = Member.Status.VISITOR
        member.first_visit_date = service.date
        member.save()
        Attendance.objects.create(service=service, member=member, recorded_by=request.user)
        return checkin_update(request, service, visitor_form=QuickVisitorForm(), added=member)
    return render(request, "attendance/partials/visitor_form.html", {
        "service": service, "visitor_form": form,
    })


@permission_required("attendance.delete_service")
def service_delete(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == "POST":
        label = str(service)
        service.delete()
        messages.success(request, f"{label} was deleted.")
        return redirect("attendance:service_list")
    return render(request, "attendance/service_confirm_delete.html", {"service": service})
