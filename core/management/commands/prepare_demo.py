"""
Get a recorded demo ready: a presenter with a QR code, and a demo service open all day so the kiosk
checks them in whenever the recording happens.

    python manage.py prepare_demo "First Last" [--title Bro.] [--days 3]
    python manage.py prepare_demo "First Last" --reset      # undo today's check-in for another take
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from attendance.models import Attendance, Service, ServiceType
from checkin.models import CheckinCard
from checkin.services import issue_card
from members.models import Member

DEMO_TYPE = "Flock Demo"


class Command(BaseCommand):
    help = "Prepare a presenter (with a QR code) and an all-day demo service for a recorded demo."

    def add_arguments(self, parser):
        parser.add_argument("name", help='Presenter\'s name, e.g. "Juan Dela Cruz" (last word = last name)')
        parser.add_argument("--title", default="Bro.", help="Bro., Sis., Pastor or Deacon")
        parser.add_argument("--days", type=int, default=3, help="Open a demo service today and the next days")
        parser.add_argument("--reset", action="store_true", help="Undo the presenter's check-ins on demo days")

    def handle(self, name, title, days, reset, **options):
        *first, last = name.split()
        first = " ".join(first) or last
        member, created = Member.objects.get_or_create(
            first_name=first, last_name=last,
            defaults={"title": title, "status": Member.Status.MEMBER, "church_role": "Flock demo"},
        )
        card = getattr(member, "checkin_card", None) or issue_card(member)

        # A service type that never opens by itself (no usual day), with no time: the kiosk treats an
        # untimed service as open all day, so the check-in works whenever the demo is recorded.
        demo_type, _ = ServiceType.objects.get_or_create(
            name=DEMO_TYPE, defaults={"weekday": None, "start_time": None, "order": 99})
        today = timezone.localdate()
        demo_days = [today + timedelta(days=d) for d in range(days)]
        for day in demo_days:
            Service.objects.get_or_create(service_type=demo_type, date=day, defaults={"title": "Flock Demo Service"})

        if reset:
            gone, _ = Attendance.objects.filter(member=member, service__date__in=demo_days).delete()
            self.stdout.write(f"Removed {gone} check-in(s) for {member.display_name}: ready for another take.")

        service = Service.objects.get(service_type=demo_type, date=today)
        self.stdout.write(self.style.SUCCESS(
            f"{'Created' if created else 'Using'} {member.display_name} (member #{member.pk}), QR {card.qr_text}\n"
            f"Demo service open all day: {', '.join(d.strftime('%a %b %d') for d in demo_days)}\n"
            f"  Profile:   /members/{member.pk}/\n"
            f"  Sticker:   /checkin/stickers/?member={member.pk}\n"
            f"  Kiosk:     /checkin/kiosk/\n"
            f"  Check-in:  /attendance/services/{service.pk}/   (watch it appear live)"
        ))
        if CheckinCard.objects.filter(member=member).count() != 1:
            self.stdout.write(self.style.WARNING("Unexpected: more than one QR card."))
