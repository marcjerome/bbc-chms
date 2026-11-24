import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from attendance.models import Attendance, Service, ServiceType
from members.models import Household, Member

FAMILIES = ["Dela Cruz", "Agbayani", "Ramos", "Pascua", "Ventura", "Corpuz", "Flores", "Manzano",
            "Bautista", "Galano", "Tolentino", "Salvador"]
MALE = ["Jose", "Mark", "Paolo", "Ramon", "Daniel", "Joshua", "Samuel", "Noel", "Rey", "Caleb"]
FEMALE = ["Maria", "Grace", "Joy", "Ruth", "Hannah", "Liza", "Faith", "Rachel", "Mae", "Esther"]


class Command(BaseCommand):
    help = "Fill an EMPTY database with fictional demo members and attendance (for testing only)."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Seed even if members already exist.")

    def handle(self, *args, force=False, **options):
        if Member.objects.exists() and not force:
            self.stdout.write("Members already exist; skipping demo data (use --force).")
            return
        rng = random.Random(42)
        today = timezone.localdate()
        members = []
        for family in FAMILIES:
            hh = Household.objects.create(name=f"{family} Family", address_line=f"Purok {rng.randint(1, 7)}")
            status = rng.choice([Member.Status.MEMBER] * 3 + [Member.Status.ATTENDEE])
            head = Member.objects.create(
                title="Bro.", church_role=rng.choice(["", "", "Usher", "Deacon", "Song Leader"]),
                first_name=rng.choice(MALE), last_name=family, gender="M", household=hh,
                household_role="head", status=status, civil_status="married",
                birth_date=date(rng.randint(1960, 1990), rng.randint(1, 12), rng.randint(1, 28)),
                phone=f"09{rng.randint(100000000, 999999999)}", is_baptized=status == "member",
            )
            spouse = Member.objects.create(
                title="Sis.", first_name=rng.choice(FEMALE), last_name=family, gender="F", household=hh,
                household_role="spouse", status=status, civil_status="married",
                birth_date=date(rng.randint(1962, 1992), rng.randint(1, 12), rng.randint(1, 28)),
                is_baptized=status == "member",
            )
            members += [head, spouse]
            for _ in range(rng.randint(0, 3)):
                gender = rng.choice("MF")
                members.append(Member.objects.create(
                    first_name=rng.choice(MALE if gender == "M" else FEMALE), last_name=family,
                    gender=gender, household=hh, household_role="child",
                    status=rng.choice([Member.Status.ATTENDEE, Member.Status.MEMBER]),
                    birth_date=date(rng.randint(2005, 2020), rng.randint(1, 12), rng.randint(1, 28)),
                ))
        for i in range(5):
            members.append(Member.objects.create(
                first_name=rng.choice(MALE + FEMALE), last_name=rng.choice(["Santos", "Reyes", "Garcia"]),
                status=Member.Status.VISITOR, first_visit_date=today - timedelta(days=i * 6),
            ))

        worship = ServiceType.objects.filter(name="Sunday Worship").first() or ServiceType.objects.first()
        if worship:
            last_sunday = today - timedelta(days=(today.weekday() - 6) % 7)
            for week in range(8):
                service = Service.objects.create(
                    service_type=worship, date=last_sunday - timedelta(weeks=week),
                    guest_headcount=rng.randint(0, 8),
                )
                for m in members:
                    if rng.random() < 0.7:
                        Attendance.objects.create(service=service, member=m)
        from django.conf import settings

        if settings.SELF_CHECKIN_ENABLED:
            from checkin.services import issue_card

            regulars = [m for m in members if m.status != Member.Status.VISITOR]
            for n, m in enumerate(regulars[: int(len(regulars) * 0.6)]):
                card = issue_card(m)
                if n % 4:
                    card.printed_at = timezone.now()
                    card.save(update_fields=["printed_at"])
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(members)} demo members."))
