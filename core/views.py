from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.shortcuts import redirect, render
from django.utils import timezone

from attendance.models import Service, ServiceType
from members.birthdays import birthdays_in_week
from members.followups import absentees, recent_visitors
from members.models import Member


@login_required
def dashboard(request):
    if not request.user.has_perm("members.view_member"):
        # A kiosk-only account (a device at the door) must not see names, birthdays or who was missed.
        if request.user.has_perm("checkin.add_scan"):
            return redirect("checkin:kiosk")
        raise PermissionDenied
    today = timezone.localdate()
    month_start = today.replace(day=1)
    active = Member.objects.filter(status__in=Member.ACTIVE_STATUSES)

    stats = {
        "active": active.count(),
        "members": Member.objects.filter(status=Member.Status.MEMBER).count(),
        "visitors_month": Member.objects.filter(
            status=Member.Status.VISITOR, first_visit_date__gte=month_start
        ).count(),
    }

    # Weekly trend for the main (first-ordered) service type over the last 8 weeks.
    main_type = ServiceType.objects.filter(is_active=True).first()
    trend = []
    if main_type:
        since = today - timedelta(weeks=8)
        services = (
            Service.objects.filter(service_type=main_type, date__gte=since, date__lte=today)
            .annotate(present=Count("attendances"))
            .order_by("date")
        )
        trend = [
            {"date": s.date, "total": s.present + s.guest_headcount, "guests": s.guest_headcount, "pk": s.pk}
            for s in services
        ]
    summary = None
    if trend:
        totals = [t["total"] for t in trend]
        peak = max(totals) or 1
        for t in trend:
            t["pct"] = round(t["total"] / peak * 100)
            t["is_today"] = t["date"] == today
        grand = sum(totals)
        summary = {
            "average": round(grand / len(totals)),
            "peak": max(totals),
            "guest_ratio": round(sum(t["guests"] for t in trend) / grand * 100, 1) if grand else 0,
        }
    stats["last_service"] = trend[-1]["total"] if trend else None
    stats["last_service_date"] = trend[-1]["date"] if trend else None
    # Progress-bar widths for the stat cards (0-100).
    stats["members_pct"] = round(stats["members"] / stats["active"] * 100) if stats["active"] else 0
    stats["visitors_pct"] = min(100, round(stats["visitors_month"] / stats["active"] * 100 * 4)) if stats["active"] else 0
    stats["last_pct"] = round(stats["last_service"] / summary["peak"] * 100) if summary and summary["peak"] else 0
    absent, absent_services = absentees()

    week_start, week_end, birthdays = birthdays_in_week(today)
    recent_services = (
        Service.objects.select_related("service_type")
        .annotate(present=Count("attendances"))
        .order_by("-date", "service_type__order")[:6]
    )
    return render(request, "core/dashboard.html", {
        "stats": stats,
        "main_type": main_type,
        "trend": trend,
        "summary": summary,
        "followup_visitors": recent_visitors().count(),
        "followup_absent": absent.count(),
        "absent_service": absent_services[0] if absent_services else None,
        "birthdays": birthdays,
        "week_start": week_start,
        "week_end": week_end,
        "recent_services": recent_services,
        "today": today,
    })
