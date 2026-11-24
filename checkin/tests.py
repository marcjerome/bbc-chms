from datetime import date, datetime, time, timedelta

from django.contrib.auth.models import Group, User
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from attendance.models import Attendance, Service, ServiceType
from core.tests import BaseTestCase

from .models import CheckinCard, Scan
from .services import find_service, issue_card, normalize_code, record_scan

SUNDAY = date(2026, 11, 22)


def at(hour, minute=0, day=SUNDAY):
    return timezone.make_aware(datetime.combine(day, time(hour, minute)))


class CardTests(BaseTestCase):
    def test_issue_and_reissue(self):
        card = issue_card(self.juan, self.admin)
        old = card.qr_text
        self.assertTrue(old.startswith("FLOCK-"))
        self.assertEqual(len(card.code), 8)
        card.printed_at = timezone.now()
        card.save()
        card = issue_card(self.juan, self.admin)
        self.assertNotEqual(card.qr_text, old)
        self.assertIsNone(card.printed_at)  # new code needs a new sticker
        self.assertEqual(CheckinCard.objects.count(), 1)
        self.assertEqual(record_scan(old, at(9, 20)).result, "unknown_code")  # lost sticker no longer works

    def test_code_normalization(self):
        self.assertEqual(normalize_code(" flock-7kq2 m9xh\n"), "7KQ2M9XH")
        self.assertEqual(normalize_code("7KQ2M9XH"), "7KQ2M9XH")


class ScanTests(BaseTestCase):
    def test_auto_opens_and_picks_closest_service(self):
        # setup_roles seeds Sunday School 8:30 and Sunday Worship 9:30 on Sundays.
        self.assertEqual(find_service(at(9, 20)).service_type.name, "Sunday Worship")
        self.assertEqual(find_service(at(8, 25)).service_type.name, "Sunday School")
        self.assertTrue(Service.objects.filter(date=SUNDAY).count() >= 3)

    def test_outside_any_window(self):
        self.assertIsNone(find_service(at(9, 0, day=date(2026, 11, 24))))  # Tuesday: nothing scheduled

    def test_rescheduled_time_is_respected(self):
        afternoon = Service.objects.create(service_type=self.worship, date=date(2026, 11, 28), start_time=time(16, 0))
        self.assertEqual(find_service(at(15, 50, day=date(2026, 11, 28))), afternoon)

    def test_scan_checks_in_then_duplicate_then_unknown(self):
        card = issue_card(self.juan)
        first = record_scan(card.qr_text, at(9, 20), self.usher, "Main door")
        self.assertEqual(first.result, "checked_in")
        att = Attendance.objects.get(member=self.juan)
        self.assertEqual(att.source, "qr")
        self.assertEqual(att.checked_in_at, at(9, 20))
        self.assertEqual(att.service.service_type.name, "Sunday Worship")
        self.assertEqual(record_scan(card.code.lower(), at(9, 25)).result, "duplicate")
        self.assertEqual(record_scan("https://example.com", at(9, 26)).result, "unknown_code")
        self.assertEqual(Attendance.objects.count(), 1)

    def test_morning_and_afternoon_on_the_same_day(self):
        # A one-off afternoon event (e.g. a church anniversary at 2 PM) scheduled ahead on a Sunday.
        anniversary = ServiceType.objects.create(name="Special event")
        event = Service.objects.create(service_type=anniversary, date=SUNDAY, start_time=time(14, 0), title="Church Anniversary")
        card = issue_card(self.juan)
        morning = record_scan(card.qr_text, at(9, 20))
        self.assertEqual(morning.result, "checked_in")
        self.assertEqual(morning.service.service_type.name, "Sunday Worship")  # still opens by itself
        self.assertEqual(record_scan(card.qr_text, at(9, 40)).result, "duplicate")  # twice in the morning: counted once
        self.assertEqual(record_scan(card.qr_text, at(12, 50)).result, "no_service")  # lunch: no service yet
        afternoon = record_scan(card.qr_text, at(13, 30))  # 30 minutes before the event
        self.assertEqual((afternoon.result, afternoon.service), ("checked_in", event))
        self.assertEqual(Attendance.objects.filter(member=self.juan).count(), 2)  # one per service

    def test_moved_service_is_not_opened_on_its_usual_day(self):
        # Sunday Worship moved to Saturday this week: no second Worship appears on Sunday.
        Service.objects.create(service_type=self.worship, date=SUNDAY - timedelta(days=1), start_time=time(17, 0))
        Service.objects.create(service_type=ServiceType.objects.create(name="Special event"), date=SUNDAY, start_time=time(14, 0))
        find_service(at(9, 30))
        self.assertFalse(Service.objects.filter(service_type=self.worship, date=SUNDAY).exists())
        self.assertTrue(Service.objects.filter(service_type__name="Sunday School", date=SUNDAY).exists())  # others still open

    def test_extra_occurrence_with_a_title_is_not_a_move(self):
        # "Christmas Eve" on Thursday using the Sunday Worship type: Sunday's worship still opens.
        Service.objects.create(service_type=self.worship, date=SUNDAY - timedelta(days=3), start_time=time(19, 0), title="Christmas Eve")
        self.assertEqual(find_service(at(9, 30)).service_type, self.worship)
        self.assertEqual(find_service(at(9, 30)).date, SUNDAY)

    def test_no_service(self):
        card = issue_card(self.juan)
        scan = record_scan(card.qr_text, at(9, 0, day=date(2026, 11, 24)))
        self.assertEqual(scan.result, "no_service")
        self.assertEqual(scan.member, self.juan)


class UiTests(BaseTestCase):
    def test_member_card_flow(self):
        self.login()
        url = self.juan.get_absolute_url()
        self.assertContains(self.client.get(url), "Give QR code")
        self.client.post(reverse("checkin:issue", args=[self.juan.pk]))
        card = CheckinCard.objects.get(member=self.juan)
        self.assertContains(self.client.get(url), card.qr_text)
        svg = self.client.get(reverse("checkin:qr", args=[self.juan.pk]))
        self.assertEqual(svg["Content-Type"], "image/svg+xml")
        self.assertIn(b'xmlns="http://www.w3.org/2000/svg"', svg.content)  # needed to load as <img>
        self.client.post(reverse("checkin:revoke", args=[self.juan.pk]))
        self.assertFalse(CheckinCard.objects.exists())

    def test_stickers_bulk_issue_and_mark_printed(self):
        self.login()
        page = self.client.get(reverse("checkin:stickers"))
        self.assertContains(page, "have no QR code yet")
        self.client.post(reverse("checkin:issue_many"), {"member": [self.juan.pk, self.maria.pk]})
        self.assertEqual(CheckinCard.objects.count(), 2)
        page = self.client.get(reverse("checkin:stickers"))
        self.assertContains(page, CheckinCard.objects.get(member=self.juan).qr_text)
        self.client.post(reverse("checkin:mark_printed"), {"member": [self.juan.pk]})
        page = self.client.get(reverse("checkin:stickers"))  # default: not printed yet
        self.assertNotContains(page, CheckinCard.objects.get(member=self.juan).qr_text)
        self.assertContains(page, CheckinCard.objects.get(member=self.maria).qr_text)

    def test_kiosk_scan(self):
        card = issue_card(self.juan)
        self.login()
        self.assertContains(self.client.get(reverse("checkin:kiosk")), "Hold your Bible")
        resp = self.client.post(reverse("checkin:scan"), {"code": card.qr_text, "when": "2026-11-22T09:15", "station": "Main door"})
        self.assertContains(resp, "Welcome, Juan Dela Cruz!")
        self.assertContains(self.client.get(reverse("checkin:overview")), "Juan Dela Cruz")
        self.assertEqual(Scan.objects.get().station, "Main door")

    def test_usher_cannot_fake_scan_time(self):
        card = issue_card(self.juan)
        self.login(self.usher)
        self.client.post(reverse("checkin:scan"), {"code": card.qr_text, "when": "2026-11-22T09:15"})
        self.assertNotEqual(Scan.objects.get().scanned_at, at(9, 15))

    def test_kiosk_role_only_scans(self):
        kiosk = User.objects.create_user("door", password="pw")
        kiosk.groups.add(Group.objects.get(name="Check-in Kiosk"))
        self.login(kiosk)
        self.assertEqual(self.client.get(reverse("checkin:kiosk")).status_code, 200)
        self.assertEqual(self.client.get(reverse("checkin:stickers")).status_code, 403)
        self.assertEqual(self.client.get(reverse("members:member_list")).status_code, 403)
        self.assertRedirects(self.client.get(reverse("dashboard")), reverse("checkin:kiosk"))  # no names on the dashboard
        self.assertEqual(self.client.get(reverse("checkin:overview")).status_code, 403)

    def test_usher_cannot_issue_codes(self):
        self.login(self.usher)
        self.client.post(reverse("checkin:issue", args=[self.juan.pk]))
        self.assertFalse(CheckinCard.objects.exists())

    @override_settings(SELF_CHECKIN_ENABLED=False)
    def test_feature_switch_hides_everything(self):
        self.login()
        self.assertEqual(self.client.get(reverse("checkin:overview")).status_code, 404)
        self.assertEqual(self.client.get(reverse("checkin:kiosk")).status_code, 404)
        page = self.client.get(self.juan.get_absolute_url()).content.decode()
        self.assertNotIn("Give QR code", page)
        self.assertNotIn("Self check-in</a>", self.client.get(reverse("dashboard")).content.decode())


class QrImageTests(BaseTestCase):
    def test_standard_qr_not_micro(self):
        import re

        from .services import qr_svg

        # Micro QR is 17 modules or fewer (23 with the 3-module border); phone cameras and jsQR can't read it.
        width = int(re.search(r'width="(\d+)"', qr_svg("FLOCK-7KQ2M9XH", scale=1)).group(1))
        self.assertGreaterEqual(width, 21 + 6)


def set_modes(qr=True, fingerprint=False, face=False):
    from .models import CheckinSettings

    s = CheckinSettings.load()
    s.qr_enabled, s.fingerprint_enabled, s.face_enabled = qr, fingerprint, face
    s.save()


class ModeTests(BaseTestCase):
    def test_qr_is_the_only_default_mode(self):
        from .feature import modes

        self.assertEqual(modes(), {"qr"})

    def test_admin_switches_modes_on_the_modes_page(self):
        from .feature import modes

        self.login()
        page = self.client.get(reverse("checkin:modes"))
        self.assertContains(page, "QR stickers")
        resp = self.client.post(reverse("checkin:modes"), {"qr_enabled": "on", "face_enabled": "on", "face_match_threshold": "0.45"})
        self.assertRedirects(resp, reverse("checkin:modes"))
        self.assertEqual(modes(), {"qr", "face"})

    def test_threshold_must_be_sensible(self):
        self.login()
        resp = self.client.post(reverse("checkin:modes"), {"qr_enabled": "on", "face_match_threshold": "2"})
        self.assertContains(resp, "0.30 (strict)")

    def test_only_admins_change_modes(self):
        self.login(self.usher)
        self.assertEqual(self.client.get(reverse("checkin:modes")).status_code, 403)

    def test_qr_off_hides_qr_pages_but_keeps_face_kiosk(self):
        set_modes(qr=False, face=True)
        self.login()
        self.assertEqual(self.client.get(reverse("checkin:stickers")).status_code, 404)
        self.assertEqual(self.client.post(reverse("checkin:scan"), {"code": "X"}).status_code, 404)
        kiosk = self.client.get(reverse("checkin:kiosk"))
        self.assertContains(kiosk, "Look at the camera to check in")
        self.assertNotContains(kiosk, "jsQR.js")
        self.assertNotContains(self.client.get(self.juan.get_absolute_url()), "Give QR code")

    def test_all_modes_off(self):
        set_modes(qr=False)
        self.login()
        self.assertEqual(self.client.get(reverse("checkin:kiosk")).status_code, 404)
        self.assertContains(self.client.get(reverse("checkin:overview")), "Every check-in mode is off")
        self.assertEqual(self.client.get(reverse("checkin:modes")).status_code, 200)  # so it can be turned back on

    def test_station_can_narrow_its_modes(self):
        set_modes(qr=True, face=True)
        self.login()
        kiosk = self.client.get(reverse("checkin:kiosk"))
        self.assertContains(kiosk, "Hold up your Bible's QR code, or look at the camera")
        self.assertNotContains(kiosk, "{#")  # a template comment leaking onto the page
        self.assertContains(self.client.get(reverse("checkin:kiosk") + "?modes=qr"), "Hold your Bible's QR code up to the camera")


def face(seed, noise=0.0):
    """A fake 128-number face descriptor; small noise = the same person in another picture."""
    import random

    base = random.Random(seed)
    jitter = random.Random(seed * 1000 + int(noise * 1000))
    return [base.uniform(-0.15, 0.15) + jitter.uniform(-noise, noise) for _ in range(128)]


class FaceTests(BaseTestCase):
    def setUp(self):
        from biometrics.services import record_consent

        set_modes(qr=True, face=True)
        record_consent(self.juan, self.admin, "F-1")

    def enroll(self, member=None, seed=1):
        from .services import enroll_face

        return enroll_face(member or self.juan, [face(seed, 0.01 * k) for k in range(1, 6)], self.admin)

    def test_enrollment_needs_consent(self):
        from .services import ConsentRequired, enroll_face

        with self.assertRaises(ConsentRequired):
            enroll_face(self.maria, [face(2)] * 5)

    def test_enrollment_rejects_bad_numbers(self):
        from .services import enroll_face

        with self.assertRaises(ValueError):
            enroll_face(self.juan, [[0.1] * 127, ["x"] * 128, [float("nan")] * 128])

    def test_recognised_face_checks_in(self):
        from .services import record_face_scan

        self.enroll()
        scan = record_face_scan(face(1, 0.02), at(9, 20))
        self.assertEqual(scan.result, "checked_in")
        self.assertEqual(scan.member, self.juan)
        self.assertEqual(Attendance.objects.get().source, "face")
        self.assertEqual(record_face_scan(face(1, 0.03), at(9, 25)).result, "duplicate")

    def test_stranger_is_not_checked_in(self):
        from .services import record_face_scan

        self.enroll()
        scan = record_face_scan(face(99), at(9, 20))
        self.assertEqual(scan.result, "unknown_face")
        self.assertIsNone(scan.member)
        self.assertFalse(Attendance.objects.exists())

    def test_closest_person_wins(self):
        from biometrics.services import record_consent

        from .services import best_face_match

        record_consent(self.maria, self.admin)
        self.enroll()
        self.enroll(self.maria, seed=2)
        self.assertEqual(best_face_match(face(2, 0.02))[0], self.maria)
        self.assertEqual(best_face_match(face(1, 0.02))[0], self.juan)

    def test_withdrawing_consent_deletes_the_face(self):
        from biometrics.services import withdraw_consent

        from .models import FaceProfile

        self.enroll()
        withdraw_consent(self.juan)
        self.assertFalse(FaceProfile.objects.exists())

    def test_kiosk_face_endpoint(self):
        import json

        self.enroll()
        from attendance.models import ServiceType

        anytime = ServiceType.objects.create(name="Any time", weekday=None, start_time=None)
        Service.objects.create(service_type=anytime, date=timezone.localdate())  # no time: open all day, whenever the test runs
        kiosk = User.objects.create_user("door", password="pw")
        kiosk.groups.add(Group.objects.get(name="Check-in Kiosk"))
        self.login(kiosk)
        resp = self.client.post(reverse("checkin:face_scan"), {"descriptor": json.dumps(face(1, 0.02))})
        self.assertContains(resp, "Welcome, Juan Dela Cruz!")
        self.assertEqual(self.client.post(reverse("checkin:face_scan"), {"descriptor": "[1,2]"}).status_code, 400)
        resp = self.client.post(reverse("checkin:face_scan"), {"descriptor": json.dumps(face(50))})
        self.assertContains(resp, "We don't recognise you yet")

    def test_face_endpoint_off_when_face_mode_off(self):
        import json

        set_modes(qr=True)
        self.login()
        self.assertEqual(self.client.post(reverse("checkin:face_scan"), {"descriptor": json.dumps(face(1))}).status_code, 404)

    def test_enroll_page_and_profile_card(self):
        import json

        self.login()
        profile = self.juan.get_absolute_url()
        self.assertContains(self.client.get(profile), "Enroll face")
        self.assertContains(self.client.get(reverse("checkin:face_enroll", args=[self.juan.pk])), "Save face")
        resp = self.client.post(reverse("checkin:face_enroll", args=[self.juan.pk]),
                                {"descriptors": json.dumps([face(1, 0.01 * k) for k in range(1, 6)])})
        self.assertRedirects(resp, profile)
        self.assertContains(self.client.get(profile), "Remove face")
        self.client.post(reverse("checkin:face_remove", args=[self.juan.pk]))
        self.assertContains(self.client.get(profile), "Enroll face")

    def test_enroll_page_without_consent_goes_back(self):
        self.login()
        self.assertRedirects(self.client.get(reverse("checkin:face_enroll", args=[self.maria.pk])), self.maria.get_absolute_url())


class SeasonTests(BaseTestCase):
    def test_automatic_christmas_from_dec_1_to_jan_6(self):
        from .models import CheckinSettings

        s = CheckinSettings.load()
        self.assertEqual(s.kiosk_season, "auto")
        self.assertEqual(s.season_on(date(2026, 11, 30)), "")
        self.assertEqual(s.season_on(date(2026, 12, 1)), "christmas")
        self.assertEqual(s.season_on(date(2027, 1, 6)), "christmas")
        self.assertEqual(s.season_on(date(2027, 1, 7)), "")
        s.kiosk_season = "christmas"
        self.assertEqual(s.season_on(date(2026, 7, 1)), "christmas")
        s.kiosk_season = "off"
        self.assertEqual(s.season_on(date(2026, 12, 25)), "")

    def test_kiosk_decorations_and_merry_christmas(self):
        from .models import CheckinSettings

        self.login()
        s = CheckinSettings.load(); s.kiosk_season = "off"; s.save()
        self.assertNotContains(self.client.get(reverse("checkin:kiosk")), 'data-season="christmas"')
        self.client.post(reverse("checkin:modes"), {"qr_enabled": "on", "face_match_threshold": "0.45", "kiosk_season": "christmas"})
        self.assertEqual(CheckinSettings.load().kiosk_season, "christmas")
        page = self.client.get(reverse("checkin:kiosk"))
        self.assertContains(page, 'data-season="christmas"')
        self.assertContains(page, "Luke 2:11")
        self.assertNotContains(page, "{#")
        card = issue_card(self.juan)
        service = Service.objects.create(service_type=self._anytime(), date=timezone.localdate())
        resp = self.client.post(reverse("checkin:scan"), {"code": card.code})
        self.assertContains(resp, "Welcome")
        self.assertContains(resp, "Merry Christmas!")
        self.assertTrue(Attendance.objects.filter(service=service, member=self.juan).exists())

    def _anytime(self):
        from attendance.models import ServiceType

        return ServiceType.objects.create(name="Any time", weekday=None, start_time=None)
