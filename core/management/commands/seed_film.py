"""Fictional data for the pitch video (run only against the film database)."""
import random
from datetime import date, datetime, time, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from attendance.models import Attendance, Service, ServiceType
from checkin.services import issue_card
from members.models import Household, Member

SURNAMES = ["Agbayani", "Ramos", "Pascua", "Corpuz", "Flores", "Manzano", "Bautista", "Galano", "Tolentino",
            "Salvador", "Domingo", "Valdez", "Navarro", "Ranada", "Castro", "Fernandez", "Guerrero", "Lagmay",
            "Mamaril", "Quiocho", "Ruiz", "Sabio", "Tabije", "Ulep", "Viernes", "Ines", "Jacinto", "Lorenzo"]
MALE = ["Jose", "Mark", "Paolo", "Ramon", "Daniel", "Joshua", "Samuel", "Noel", "Rey", "Caleb", "Andres",
        "Benjie", "Dennis", "Efren", "Gilbert", "Jun", "Leo", "Nestor", "Romy", "Virgilio"]
FEMALE = ["Maria", "Grace", "Joy", "Ruth", "Hannah", "Liza", "Faith", "Rachel", "Mae", "Esther", "Analyn",
          "Cora", "Divina", "Elena", "Fe", "Gloria", "Imelda", "Jocelyn", "Marites", "Rosalie"]
ROLES = ["Deacon", "Usher", "Song Leader", "Sunday School Teacher", "Youth Leader", "Pianist"]


class Command(BaseCommand):
    def handle(self, *args, **opts):
        if "film" not in str(settings.DATABASES["default"]["NAME"]):
            raise CommandError("Refusing: run with --settings=config.settings.film")
        rng = random.Random(7)
        call_command("setup_roles", stdout=open("/dev/null", "w"))
        pastor = User.objects.create_superuser("pastor", "", "flock", first_name="Pastor")
        today = timezone.localdate()
        people = []
        for i, fam in enumerate(SURNAMES):
            hh = Household.objects.create(name=f"{fam} Family", address_line=f"Purok {rng.randint(1, 7)}")
            st = Member.Status.MEMBER if i % 4 else Member.Status.ATTENDEE
            dad = Member.objects.create(title="Bro.", first_name=rng.choice(MALE), last_name=fam, gender="M",
                household=hh, household_role="head", status=st, civil_status="married", is_baptized=st == "member",
                church_role=ROLES[i] if i < len(ROLES) else "", phone=f"0917{rng.randint(1000000, 9999999)}",
                birth_date=date(rng.randint(1958, 1990), rng.randint(1, 12), rng.randint(1, 28)),
                salvation_date=date(rng.randint(1995, 2015), rng.randint(1, 12), rng.randint(1, 28)))
            if st == "member":
                dad.baptism_date = dad.salvation_date + timedelta(days=60)
                dad.membership_date = dad.baptism_date + timedelta(days=14)
                dad.save()
            mom = Member.objects.create(title="Sis.", first_name=rng.choice(FEMALE), last_name=fam, gender="F",
                household=hh, household_role="spouse", status=st, civil_status="married", is_baptized=st == "member",
                phone=f"0918{rng.randint(1000000, 9999999)}",
                birth_date=date(rng.randint(1960, 1992), rng.randint(1, 12), rng.randint(1, 28)))
            people += [dad, mom]
            for _ in range(rng.randint(0, 2)):
                g = rng.choice("MF")
                people.append(Member.objects.create(title="Bro." if g == "M" else "Sis.",
                    first_name=rng.choice(MALE if g == "M" else FEMALE), last_name=fam, gender=g, household=hh,
                    household_role="child", status=Member.Status.ATTENDEE,
                    birth_date=date(rng.randint(2004, 2014), rng.randint(1, 12), rng.randint(1, 28))))
        # Birthdays this week (Sun-Sat) for the announcement scene
        week_start = today - timedelta(days=(today.weekday() + 1) % 7)
        for k, m in enumerate(rng.sample(people, 4)):
            d = week_start + timedelta(days=k * 2)
            m.birth_date = m.birth_date.replace(month=d.month, day=d.day)
            m.save()
        for k in range(5):
            Member.objects.create(first_name=rng.choice(MALE + FEMALE), last_name=rng.choice(["Santos", "Reyes", "Garcia", "Cruz"]),
                                  status=Member.Status.VISITOR, first_visit_date=today - timedelta(days=k * 3),
                                  phone=f"0919{rng.randint(1000000, 9999999)}")
        Member.objects.update(created_at=timezone.now() - timedelta(days=200))
        # 12 weeks of rising Sunday Worship attendance (growth story)
        worship = ServiceType.objects.get(name="Sunday Worship")
        last_sunday = today - timedelta(days=(today.weekday() - 6) % 7)
        for w in range(11, -1, -1):
            s = Service.objects.create(service_type=worship, date=last_sunday - timedelta(weeks=w), guest_headcount=4 + (11 - w))
            p = 0.55 + (11 - w) * 0.028
            Attendance.objects.bulk_create([Attendance(service=s, member=m) for m in people if rng.random() < p])
        # Self check-in: most regulars have a printed QR sticker; a few left for the "Give QR code" scene
        regulars = [m for m in people if m.household_role in ("head", "spouse")]
        for m in regulars[:40]:
            card = issue_card(m, pastor)
            card.printed_at = timezone.now()
            card.save(update_fields=["printed_at"])
        # Next Sunday's service for the live check-in scene, with a few usher check-ins already
        nxt = Service.objects.create(service_type=worship, date=last_sunday + timedelta(weeks=1), start_time=time(9, 30))
        for k, m in enumerate([m for m in people if m.household_role == "child"][:12]):
            a = Attendance.objects.create(service=nxt, member=m)
            Attendance.objects.filter(pk=a.pk).update(
                checked_in_at=timezone.make_aware(datetime.combine(nxt.date, time(9, 2 + k))))
        self.stdout.write(f"film data: {Member.objects.count()} people, next service id {nxt.pk}, "
                          f"no-QR example id {regulars[45].pk} ({regulars[45].display_name})")
