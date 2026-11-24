"""
Reset the database to a known state for the Playwright end-to-end tests (e2e/).

DESTRUCTIVE: wipes every table. It refuses to run unless the server was started for E2E testing
(environment variable E2E=1, set only by docker-compose.e2e.yml).
"""

import os
from datetime import date
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from attendance.models import Service, ServiceType
from checkin.models import CheckinCard
from checkin.services import qr_svg
from members.models import Household, Member

PASSWORD = "e2e-pass-123"
USERS = {"admin": "Church Admin", "secretary": "Secretary", "usher": "Usher", "kiosk": "Check-in Kiosk"}

# Fixed QR codes, one per kiosk test so the tests don't trip over each other's check-ins.
CARDS = {
    "KIOSKAAA": ("Bro.", "Andres", "Kiosk"),
    "KIOSKBBB": ("Sis.", "Bella", "Kiosk"),
    "KIOSKCCC": ("Bro.", "Carlo", "Kiosk"),
    "KIOSKDDD": ("Sis.", "Dina", "Kiosk"),
    "KIOSKEEE": ("Bro.", "Elias", "Kiosk"),
    "CAMERAQR": ("Sis.", "Camila", "Camera"),  # the code in the fake webcam video
    "REISSUEX": ("Bro.", "Rafael", "Reissue"),
}
# A Sunday with no other test data: kiosk tests pretend to scan at 9:15 on this day.
KIOSK_SUNDAY = date(2026, 12, 6)


class Command(BaseCommand):
    help = "Wipe the database and load the fixed data the Playwright E2E tests expect (E2E=1 only)."

    def handle(self, *args, **options):
        if os.environ.get("E2E") != "1":
            raise CommandError("Refusing to wipe this database: set E2E=1 (only the e2e compose stack does).")
        call_command("flush", interactive=False, verbosity=0)
        call_command("setup_roles", stdout=open(os.devnull, "w"))

        for username, role in USERS.items():
            user = User.objects.create_user(username, password=PASSWORD, first_name=username.title())
            user.groups.add(Group.objects.get(name=role))

        family = Household.objects.create(name="Santos Family", address_line="Purok 2", city="Batac City")
        Member.objects.create(title="Bro.", first_name="Pedro", last_name="Santos", household=family,
                              household_role="head", status=Member.Status.MEMBER, phone="09171112222",
                              email="pedro@example.com", birth_date=date(1980, 5, 10))
        Member.objects.create(title="Sis.", first_name="Rosa", last_name="Santos", household=family,
                              household_role="spouse", status=Member.Status.MEMBER, phone="09173334444")
        Member.objects.create(first_name="Victor", last_name="Visita", status=Member.Status.VISITOR)
        Member.objects.create(first_name="Ines", last_name="Inactive", status=Member.Status.INACTIVE)
        # One person per test that checks someone in, so parallel tests never see each other's check-ins.
        Member.objects.create(title="Sis.", first_name="Pia", last_name="Phone", status=Member.Status.ATTENDEE)  # mobile
        Member.objects.create(title="Bro.", first_name="Fernando", last_name="Finger", status=Member.Status.MEMBER)  # modes
        for code, (title, first, last) in CARDS.items():
            m = Member.objects.create(title=title, first_name=first, last_name=last, status=Member.Status.ATTENDEE)
            CheckinCard.objects.create(member=m, code=code)

        # A fixed future Sunday Worship service for the usher check-in tests.
        worship = ServiceType.objects.get(name="Sunday Worship")
        Service.objects.create(service_type=worship, date=date(2026, 12, 13), title="E2E Check-in Sunday")

        # The branded sticker the fake webcam will show; e2e/global-setup.js turns it into a video.
        fixtures = Path(settings.BASE_DIR) / "e2e" / ".fixtures"
        fixtures.mkdir(parents=True, exist_ok=True)
        (fixtures / "qr-camera.svg").write_text(qr_svg("FLOCK-CAMERAQR", standalone=True))
        self.stdout.write(self.style.SUCCESS("E2E data loaded."))
