from datetime import date, timedelta

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from attendance.models import Attendance, Service, ServiceType
from members.models import Household, Member


class BaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("setup_roles", stdout=open("/dev/null", "w"))
        cls.admin = User.objects.create_user("pastor", password="pw")
        cls.admin.groups.add(Group.objects.get(name="Church Admin"))
        cls.usher = User.objects.create_user("usher", password="pw")
        cls.usher.groups.add(Group.objects.get(name="Usher"))
        cls.worship = ServiceType.objects.get(name="Sunday Worship")
        cls.hh = Household.objects.create(name="Dela Cruz Family")
        cls.juan = Member.objects.create(first_name="Juan", last_name="Dela Cruz", household=cls.hh,
                                         status=Member.Status.MEMBER, phone="09171234567")
        cls.maria = Member.objects.create(first_name="Maria", middle_name="Santos", last_name="Dela Cruz",
                                          status=Member.Status.ATTENDEE)

    def login(self, user=None):
        self.client.force_login(user or self.admin)


class AuthAndDashboardTests(BaseTestCase):
    def test_pages_require_login(self):
        for url in [reverse("dashboard"), reverse("members:member_list"), reverse("attendance:service_list")]:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 302)
            self.assertIn(reverse("login"), resp["Location"])

    def test_login_page_renders(self):
        self.assertContains(self.client.get(reverse("login")), "Bible Baptist Church Barani")

    def test_dashboard_renders_with_trend(self):
        call_command("seed_demo", "--force", stdout=open("/dev/null", "w"))
        self.login()
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["trend"]), 8)

    def test_usher_cannot_edit_members(self):
        self.login(self.usher)
        self.assertEqual(self.client.get(reverse("members:member_list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("members:member_create")).status_code, 403)


class MemberTests(BaseTestCase):
    def test_full_name_and_age(self):
        self.assertEqual(self.maria.full_name, "Maria S. Dela Cruz")
        m = Member(first_name="A", last_name="B", birth_date=date(2000, 1, 1))
        self.assertGreaterEqual(m.age, 26)

    def test_list_search_and_htmx_partial(self):
        self.login()
        resp = self.client.get(reverse("members:member_list"), {"q": "maria"})
        self.assertContains(resp, "Dela Cruz, Maria")
        self.assertNotContains(resp, "Dela Cruz, Juan")
        self.assertContains(resp, "<html")
        partial = self.client.get(reverse("members:member_list"), {"q": "0917"}, headers={"HX-Request": "true"})
        self.assertContains(partial, "Dela Cruz, Juan")
        self.assertNotContains(partial, "<html")

    def test_status_filter(self):
        self.login()
        resp = self.client.get(reverse("members:member_list"), {"status": "member"})
        self.assertEqual(resp.context["total"], 1)

    def test_create_member(self):
        self.login()
        resp = self.client.post(reverse("members:member_create"), {
            "first_name": "Pedro", "last_name": "Ramos", "status": "visitor", "baptism_date": "2020-05-01",
        })
        pedro = Member.objects.get(first_name="Pedro")
        self.assertRedirects(resp, pedro.get_absolute_url())
        self.assertTrue(pedro.is_baptized)  # implied by baptism date

    def test_household_role_requires_household(self):
        self.login()
        resp = self.client.post(reverse("members:member_create"), {
            "first_name": "X", "last_name": "Y", "status": "visitor", "household_role": "child",
        })
        self.assertFormError(resp.context["form"], "household_role", "Choose a household first.")

    def test_detail_and_export(self):
        self.login()
        self.assertContains(self.client.get(self.juan.get_absolute_url()), "Dela Cruz Family")
        csv = self.client.get(reverse("members:member_export"))
        self.assertIn("Juan", csv.content.decode())

    def test_household_pages(self):
        self.login()
        self.assertContains(self.client.get(reverse("members:household_list")), "Dela Cruz Family")
        self.assertContains(self.client.get(self.hh.get_absolute_url()), "Juan")


class AttendanceTests(BaseTestCase):
    def setUp(self):
        self.service = Service.objects.create(service_type=self.worship, date=timezone.localdate())

    def test_create_service_and_duplicate_error(self):
        self.login(self.usher)
        day = timezone.localdate() - timedelta(days=7)
        resp = self.client.post(reverse("attendance:service_list"), {"service_type": self.worship.pk, "date": day})
        self.assertEqual(resp.status_code, 302)
        resp = self.client.post(reverse("attendance:service_list"), {"service_type": self.worship.pk, "date": day})
        self.assertContains(resp, "already exists")

    def test_checkin_page_and_search_partial(self):
        self.login(self.usher)
        url = self.service.get_absolute_url()
        self.assertContains(self.client.get(url), "Search name to check in")
        resp = self.client.get(url, {"q": "juan"}, headers={"HX-Request": "true", "HX-Target": "search-results"})
        self.assertContains(resp, f'id="member-row-{self.juan.pk}"')
        self.assertNotContains(resp, "<html")

    def test_toggle_attendance_returns_oob_updates(self):
        self.login(self.usher)
        url = reverse("attendance:toggle", args=[self.service.pk, self.juan.pk])
        resp = self.client.post(url, headers={"HX-Request": "true"})
        self.assertTrue(Attendance.objects.filter(service=self.service, member=self.juan).exists())
        body = resp.content.decode()
        self.assertEqual(body.count('hx-swap-oob="true"'), 4)  # row, counters, absent count, checked-in list
        self.assertIn("btn-present", body)
        self.client.post(url)
        self.assertFalse(Attendance.objects.filter(service=self.service, member=self.juan).exists())

    def test_guest_counter_never_negative(self):
        self.login(self.usher)
        url = reverse("attendance:adjust_guests", args=[self.service.pk])
        self.client.post(url, {"delta": 1})
        self.client.post(url, {"delta": -1})
        self.client.post(url, {"delta": -1})
        self.service.refresh_from_db()
        self.assertEqual(self.service.guest_headcount, 0)

    def test_add_visitor_checks_in(self):
        self.login(self.usher)
        resp = self.client.post(reverse("attendance:add_visitor", args=[self.service.pk]),
                                {"first_name": "Ana", "last_name": "Lopez"})
        ana = Member.objects.get(first_name="Ana")
        self.assertEqual(ana.status, Member.Status.VISITOR)
        self.assertEqual(ana.first_visit_date, self.service.date)
        self.assertContains(resp, "was added and checked in")
        self.assertEqual(self.service.present_count, 1)

    def test_secretary_cannot_take_attendance(self):
        sec = User.objects.create_user("sec", password="pw")
        sec.groups.add(Group.objects.get(name="Secretary"))
        self.login(sec)
        resp = self.client.post(reverse("attendance:toggle", args=[self.service.pk, self.juan.pk]))
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(self.service.present_count, 0)


class DesignAdditionsTests(BaseTestCase):
    def test_display_name_with_title(self):
        m = Member(title="Bro.", first_name="Juan", last_name="Ramos")
        self.assertEqual(m.display_name, "Bro. Juan Ramos")

    def test_absentees_and_visitors(self):
        from members.followups import absentees, recent_visitors

        today = timezone.localdate()
        Member.objects.update(created_at=timezone.now() - timedelta(days=60))
        last = Service.objects.create(service_type=self.worship, date=today)
        Service.objects.create(service_type=self.worship, date=today - timedelta(weeks=1))
        Attendance.objects.create(service=last, member=self.juan)  # Juan came; Maria didn't
        absent, _ = absentees()
        self.assertEqual(list(absent), [self.maria])
        Member.objects.create(first_name="New", last_name="Guest", first_visit_date=today)
        self.assertEqual(recent_visitors().count(), 1)
        self.login()
        resp = self.client.get(reverse("members:followups"))
        self.assertContains(resp, "Maria")
        self.assertContains(self.client.get(reverse("dashboard")), "We missed 1 at the last Sunday Worship")

    def test_absentees_need_a_service(self):
        from members.followups import absentees

        self.assertEqual(absentees()[0].count(), 0)

    def test_remember_me_controls_session_expiry(self):
        url = reverse("login")
        self.client.post(url, {"username": "pastor", "password": "pw"})
        self.assertTrue(self.client.session.get_expire_at_browser_close())
        self.client.logout()
        self.client.post(url, {"username": "pastor", "password": "pw", "remember": "1"})
        self.assertFalse(self.client.session.get_expire_at_browser_close())

    def test_checkin_row_shows_time_and_undo(self):
        service = Service.objects.create(service_type=self.worship, date=timezone.localdate())
        self.login(self.usher)
        resp = self.client.post(reverse("attendance:toggle", args=[service.pk, self.juan.pk]))
        self.assertContains(resp, "Present ·")
        self.assertContains(resp, "Undo check-in")


class BirthdayTests(BaseTestCase):
    def test_week_is_sunday_to_saturday(self):
        from members.birthdays import week_bounds

        self.assertEqual(week_bounds(date(2026, 11, 25)), (date(2026, 11, 22), date(2026, 11, 28)))
        self.assertEqual(week_bounds(date(2026, 11, 22)), (date(2026, 11, 22), date(2026, 11, 28)))

    def test_week_spanning_new_year_and_leap_day(self):
        from members.birthdays import birthdays_in_week

        Member.objects.create(first_name="Jan", last_name="A", status="member", birth_date=date(1990, 1, 2))
        Member.objects.create(first_name="Dec", last_name="B", status="member", birth_date=date(1985, 12, 31))
        Member.objects.create(first_name="Gone", last_name="C", status="transferred", birth_date=date(1985, 12, 30))
        _, _, people = birthdays_in_week(date(2026, 12, 30))  # Sun Dec 27 – Sat Jan 2
        self.assertEqual([(p["member"].first_name, p["turning"]) for p in people], [("Dec", 41), ("Jan", 37)])
        Member.objects.create(first_name="Leap", last_name="D", status="member", birth_date=date(2000, 2, 29))
        _, _, people = birthdays_in_week(date(2027, 2, 28))
        self.assertEqual(people[0]["date"], date(2027, 2, 28))

    def test_birthdays_page(self):
        self.login()
        resp = self.client.get(reverse("members:birthdays"), {"week": "2026-12-30"})
        self.assertContains(resp, "December 27")


class ServiceManagerTests(BaseTestCase):
    def test_reschedule_one_occurrence(self):
        self.login(self.usher)
        service = Service.objects.create(service_type=self.worship, date=date(2026, 11, 29))
        self.assertFalse(service.is_rescheduled)
        resp = self.client.post(reverse("attendance:service_update", args=[service.pk]), {
            "service_type": self.worship.pk, "date": "2026-11-28", "start_time": "15:00",
        })
        self.assertRedirects(resp, service.get_absolute_url())
        service.refresh_from_db()
        self.assertTrue(service.is_rescheduled)
        self.assertEqual(service.time.hour, 15)

    def test_upcoming_listed_separately(self):
        self.login()
        Service.objects.create(service_type=self.worship, date=timezone.localdate() + timedelta(days=7))
        resp = self.client.get(reverse("attendance:service_list"))
        self.assertEqual(len(resp.context["upcoming"]), 1)

    def test_only_admin_manages_service_types(self):
        self.login(self.usher)
        self.assertEqual(self.client.get(reverse("attendance:servicetype_list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("attendance:servicetype_create")).status_code, 403)
        self.login(self.admin)
        resp = self.client.post(reverse("attendance:servicetype_create"), {
            "name": "Wednesday Prayer Meeting", "weekday": 2, "start_time": "19:00", "is_active": "on", "order": 5,
        })
        self.assertRedirects(resp, reverse("attendance:servicetype_list"))

    def test_not_checked_in_list(self):
        service = Service.objects.create(service_type=self.worship, date=timezone.localdate())
        Attendance.objects.create(service=service, member=self.juan)
        self.login(self.usher)
        resp = self.client.get(service.get_absolute_url(), {"absent": "1"},
                               headers={"HX-Request": "true", "HX-Target": "search-results"})
        self.assertContains(resp, f"member-row-{self.maria.pk}")
        self.assertNotContains(resp, f"member-row-{self.juan.pk}")


class PrivateNetworkHostTests(BaseTestCase):
    def test_private_addresses_allowed_public_refused(self):
        from django.test import override_settings

        mw = ["core.middleware.PrivateNetworkHostMiddleware", *__import__("django.conf").conf.settings.MIDDLEWARE]
        with override_settings(ALLOWED_HOSTS=["*"], LISTED_HOSTS=["flock.example.org"], MIDDLEWARE=mw):
            for host in ["192.168.1.10:8002", "10.0.0.5", "172.20.1.2:8002", "localhost:8002", "flock.local",
                         "flock.example.org"]:
                self.assertEqual(self.client.get("/login/", HTTP_HOST=host).status_code, 200, host)
            for host in ["8.8.8.8", "evil.com", "1.1.1.1:8002"]:
                self.assertEqual(self.client.get("/login/", HTTP_HOST=host).status_code, 400, host)


class MemberValidationTests(BaseTestCase):
    def form(self, **data):
        from members.forms import MemberForm

        return MemberForm({"first_name": "A", "last_name": "B", "status": "visitor", **data})

    def test_phone_numbers(self):
        for ok in ["09171234567", "0917 123 4567", "+63 917 123-4567", "(075) 123 4567"]:
            self.assertTrue(self.form(phone=ok).is_valid(), ok)
        for bad in ["call me maybe", "12345", "0917-ABC-4567", "1" * 16]:
            self.assertIn("phone", self.form(phone=bad).errors, bad)

    def test_dates(self):
        self.assertIn("birth_date", self.form(birth_date="2099-01-01").errors)
        self.assertIn("baptism_date", self.form(birth_date="2000-01-01", baptism_date="1999-01-01").errors)
        self.assertIn("membership_date", self.form(membership_date="2099-01-01").errors)
        self.assertTrue(self.form(birth_date="1990-01-01", baptism_date="2010-01-01").is_valid())
