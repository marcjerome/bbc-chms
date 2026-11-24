"""Pastoral follow-up lists: recent first-time visitors and absentees."""

from datetime import timedelta

from django.db.models import Max
from django.utils import timezone

from attendance.models import Service, ServiceType

from .models import Member

VISITOR_WINDOW_DAYS = 14
ABSENT_SERVICES = 1  # [M] Marc, 2026-11-22: missing one service = absent from that service


def main_service_type():
    return ServiceType.objects.filter(is_active=True).first()


def recent_visitors(days=VISITOR_WINDOW_DAYS):
    since = timezone.localdate() - timedelta(days=days)
    return Member.objects.filter(status=Member.Status.VISITOR, first_visit_date__gte=since).order_by(
        "-first_visit_date"
    )


def absentees(missed=ABSENT_SERVICES):
    """
    Regular attendees and members with no check-in at any of the last `missed` services of the main
    service type. People added after the earliest of those services are not flagged.
    """
    service_type = main_service_type()
    if not service_type:
        return Member.objects.none(), []
    services = list(
        Service.objects.filter(service_type=service_type, date__lte=timezone.localdate())
        .order_by("-date")[:missed]
    )
    if len(services) < missed:
        return Member.objects.none(), services
    earliest = services[-1]
    qs = (
        Member.objects.filter(
            status__in=[Member.Status.MEMBER, Member.Status.ATTENDEE],
            created_at__date__lt=earliest.date,
        )
        .exclude(attendances__service__in=services)
        .annotate(last_seen=Max("attendances__service__date"))
        .order_by("last_seen", "last_name")
    )
    return qs, services
