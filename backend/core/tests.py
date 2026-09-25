"""
API tests, organised by who is using the system.

    python manage.py test core

Viewer    — anyone on the internet, not signed in
Student   — someone filling in the QR intake form
Staff     — a counsellor, who must only ever see their own students
Admin     — the owner, who sees everything and runs reports

The throttle cache is cleared before every test so rate limits from one test
never leak into the next.
"""

from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Assignment, Country, ExportLog, Lead, Note, User


class Base(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.admin = User.objects.create_user(
            "admin", password="pw-admin-123", role=User.Role.ADMIN,
            first_name="Puja", must_change_password=False,
        )
        self.sarita = User.objects.create_user(
            "sarita", password="pw-sarita-123", first_name="Sarita",
            must_change_password=False,
        )
        self.mingma = User.objects.create_user(
            "mingma", password="pw-mingma-123", first_name="Mingma",
            must_change_password=False,
        )
        self.australia = Country.objects.create(name="Australia", slug="australia")
        self.hidden = Country.objects.create(name="Hidden", slug="hidden", is_active=False)

        self.s_lead = Lead.objects.create(full_name="Anisha", phone="9841000001",
                                          assigned_to=self.sarita, status="contacted")
        self.m_lead = Lead.objects.create(full_name="Bibek", phone="9841000002",
                                          assigned_to=self.mingma, status="contacted")
        self.free_lead = Lead.objects.create(full_name="Priyanka", phone="9841000003")

    def as_user(self, user):
        self.client.force_authenticate(user)
        return self.client

    def intake(self, **extra):
        data = {"full_name": "Ramesh", "phone": "+977 9851 111222",
                "consent_given": True, "source": "fair-jan"}
        data.update(extra)
        return self.client.post("/api/leads/intake/", data, format="json")


# ---------------------------------------------------------------------------
# Viewer
# ---------------------------------------------------------------------------

class ViewerTests(Base):
    def test_public_pages_are_open(self):
        for path in ["/api/countries/", "/api/countries/australia/",
                     "/api/batches/", "/api/counsellors/"]:
            self.assertEqual(self.client.get(path).status_code, 200, path)

    def test_inactive_country_is_hidden(self):
        names = [c["name"] for c in self.client.get("/api/countries/").json()]
        self.assertNotIn("Hidden", names)
        self.assertEqual(self.client.get("/api/countries/hidden/").status_code, 404)

    def test_unfinished_accounts_are_not_shown_publicly(self):
        User.objects.create_user("newbie", password="Temp-pass-4821", first_name="New")
        self.sarita.bio = "Handles Australia."
        self.sarita.save()
        names = [c["name"] for c in self.client.get("/api/counsellors/").json()]
        self.assertEqual(names, ["Sarita"])

    def test_counsellor_list_leaks_no_private_fields(self):
        self.sarita.bio = "Handles Australia."
        self.sarita.save()
        row = self.client.get("/api/counsellors/").json()[0]
        for private in ("username", "email", "phone", "role", "password"):
            self.assertNotIn(private, row)

    def test_every_staff_endpoint_needs_login(self):
        for path in ["/api/leads/", f"/api/leads/{self.s_lead.pk}/", "/api/dashboard/",
                     "/api/team/", "/api/reports/", "/api/leads/export/", "/api/me/"]:
            self.assertEqual(self.client.get(path).status_code, 401, path)


# ---------------------------------------------------------------------------
# Student
# ---------------------------------------------------------------------------

class StudentTests(Base):
    def test_happy_path_two_steps(self):
        r = self.intake(interested_countries=[self.australia.pk])
        self.assertEqual(r.status_code, 201)
        token = r.json()["token"]
        r = self.client.patch("/api/leads/intake/details/", {
            "token": token, "highest_qualification": "Bachelor's degree",
            "test_type": "ielts", "test_score": "6.5", "visa_history": "refused",
            "visa_history_country": "UK",
        }, format="json")
        self.assertEqual(r.status_code, 200)
        lead = Lead.objects.get(full_name="Ramesh")
        self.assertEqual(lead.source, "fair-jan")
        self.assertEqual(lead.visa_history, "refused")
        self.assertIsNotNone(lead.consent_at)

    def test_response_does_not_expose_database_ids(self):
        r = self.intake()
        self.assertNotIn("id", r.json())

    def test_validation(self):
        self.assertEqual(self.intake(consent_given=False).status_code, 400)
        self.assertEqual(self.intake(phone="123").status_code, 400)
        self.assertEqual(self.intake(full_name="").status_code, 400)
        self.assertEqual(self.intake(interested_countries=[9999]).status_code, 400)

    @override_settings(AUTO_ASSIGN=False)
    def test_cannot_set_pipeline_fields(self):
        self.intake(status="enrolled", assigned_to=self.sarita.pk)
        lead = Lead.objects.get(full_name="Ramesh")
        self.assertEqual(lead.status, "new")
        self.assertIsNone(lead.assigned_to)

    def test_honeypot_saves_nothing(self):
        before = Lead.objects.count()
        r = self.intake(website="http://spam")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Lead.objects.count(), before)

    def test_stranger_cannot_overwrite_another_students_details(self):
        """Walking IDs on step two must not reach someone else's record."""
        self.intake()
        victim = Lead.objects.get(full_name="Ramesh")
        # Old, ID-based route is gone.
        r = self.client.patch(f"/api/leads/intake/{victim.pk}/details/",
                              {"message": "hijacked"}, format="json")
        self.assertIn(r.status_code, (404, 405))
        # A made-up token is refused.
        r = self.client.patch("/api/leads/intake/details/",
                              {"token": "made-up", "message": "hijacked"}, format="json")
        self.assertEqual(r.status_code, 404)
        victim.refresh_from_db()
        self.assertEqual(victim.message, "")

    def test_duplicate_phone_in_different_format_is_merged(self):
        self.intake(phone="+977 9851 111222")
        self.intake(phone="9851111222", source="brochure")
        self.assertEqual(Lead.objects.filter(full_name="Ramesh").count(), 1)
        self.assertTrue(Note.objects.filter(body__contains="brochure").exists())

    def test_duplicate_details_become_a_note_not_an_overwrite(self):
        first = self.intake().json()["token"]
        self.client.patch("/api/leads/intake/details/",
                          {"token": first, "message": "original"}, format="json")
        second = self.intake(source="brochure").json()["token"]
        r = self.client.patch("/api/leads/intake/details/",
                              {"token": second, "message": "second visit"}, format="json")
        self.assertEqual(r.status_code, 200)
        lead = Lead.objects.get(full_name="Ramesh")
        self.assertEqual(lead.message, "original")
        self.assertTrue(lead.notes.filter(body__contains="second visit").exists())

    def test_busy_education_fair_is_not_blocked(self):
        """Dozens of students share one Wi-Fi IP at a fair."""
        for i in range(30):
            r = self.intake(phone=f"98000{i:05d}")
            self.assertEqual(r.status_code, 201, f"submission {i + 1} was blocked")


# ---------------------------------------------------------------------------
# Staff (counsellor)
# ---------------------------------------------------------------------------

class StaffTests(Base):
    def test_sees_only_own_students(self):
        ids = [r["id"] for r in self.as_user(self.sarita).get("/api/leads/").json()["results"]]
        self.assertEqual(ids, [self.s_lead.pk])

    def test_other_students_are_404_everywhere(self):
        c = self.as_user(self.sarita)
        for lead in (self.m_lead, self.free_lead):
            self.assertEqual(c.get(f"/api/leads/{lead.pk}/").status_code, 404)
            self.assertEqual(c.patch(f"/api/leads/{lead.pk}/", {"status": "lost"},
                                     format="json").status_code, 404)
            self.assertEqual(c.post(f"/api/leads/{lead.pk}/notes/", {"body": "x"},
                                    format="json").status_code, 404)

    def test_owner_endpoints_are_forbidden(self):
        c = self.as_user(self.sarita)
        for path in ["/api/team/", "/api/reports/", "/api/leads/export/"]:
            self.assertEqual(c.get(path).status_code, 403, path)
        r = c.post("/api/team/handover/",
                   {"from_user": self.mingma.pk, "to_user": self.sarita.pk}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_cannot_reassign(self):
        c = self.as_user(self.sarita)
        c.patch(f"/api/leads/{self.s_lead.pk}/", {"assigned_to": self.mingma.pk}, format="json")
        c.patch(f"/api/leads/{self.s_lead.pk}/", {"assigned_to": None}, format="json")
        self.s_lead.refresh_from_db()
        self.assertEqual(self.s_lead.assigned_to, self.sarita)

    def test_cannot_backdate_last_contacted(self):
        """Faking a call time would hide a student from the overdue list."""
        c = self.as_user(self.sarita)
        c.patch(f"/api/leads/{self.s_lead.pk}/",
                {"last_contacted_at": "2020-01-01T00:00:00Z"}, format="json")
        self.s_lead.refresh_from_db()
        self.assertIsNone(self.s_lead.last_contacted_at)

    def test_phone_is_validated_on_edit(self):
        r = self.as_user(self.sarita).patch(f"/api/leads/{self.s_lead.pk}/",
                                            {"phone": "x"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_call_log_stamps_contact_time(self):
        lead = Lead.objects.create(full_name="New one", phone="9841000009",
                                   assigned_to=self.sarita)
        r = self.as_user(self.sarita).post(f"/api/leads/{lead.pk}/notes/",
                                           {"body": "Called", "is_call_log": True},
                                           format="json")
        self.assertEqual(r.status_code, 201)
        lead.refresh_from_db()
        self.assertEqual(lead.status, "contacted")
        self.assertIsNotNone(lead.last_contacted_at)

    def test_cannot_delete(self):
        r = self.as_user(self.sarita).delete(f"/api/leads/{self.s_lead.pk}/")
        self.assertEqual(r.status_code, 405)

    def test_temporary_password_blocks_everything_until_changed(self):
        newbie = User.objects.create_user("newbie", password="Temp-pass-4821")
        c = self.as_user(newbie)
        self.assertEqual(c.get("/api/me/").status_code, 200)
        self.assertEqual(c.get("/api/leads/").status_code, 403)
        r = c.post("/api/auth/password/", {"current_password": "Temp-pass-4821",
                                           "new_password": "12345678"}, format="json")
        self.assertEqual(r.status_code, 400)
        r = c.post("/api/auth/password/", {"current_password": "Temp-pass-4821",
                                           "new_password": "Kathmandu-River-77"}, format="json")
        self.assertEqual(r.status_code, 200)
        newbie.refresh_from_db()
        self.assertEqual(c.get("/api/leads/").status_code, 200)


# ---------------------------------------------------------------------------
# Admin (owner)
# ---------------------------------------------------------------------------

class AdminTests(Base):
    def test_sees_everyone(self):
        r = self.as_user(self.admin).get("/api/leads/").json()
        self.assertEqual(r["count"], 3)

    def test_reassign_is_logged(self):
        self.as_user(self.admin).patch(f"/api/leads/{self.free_lead.pk}/",
                                       {"assigned_to": self.sarita.pk}, format="json")
        self.assertTrue(Assignment.objects.filter(lead=self.free_lead,
                                                  to_user=self.sarita).exists())

    def test_cannot_assign_to_a_closed_account(self):
        self.mingma.is_active = False
        self.mingma.save()
        r = self.as_user(self.admin).patch(f"/api/leads/{self.free_lead.pk}/",
                                           {"assigned_to": self.mingma.pk}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_reports_team_export(self):
        c = self.as_user(self.admin)
        self.assertEqual(c.get("/api/team/").status_code, 200)
        self.assertEqual(c.get("/api/reports/").status_code, 200)
        r = c.get("/api/leads/export/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.content.decode().strip().splitlines()), 4)
        self.assertEqual(ExportLog.objects.get().row_count, 3)

    def test_handover_moves_open_leads(self):
        r = self.as_user(self.admin).post("/api/team/handover/", {
            "from_user": self.mingma.pk, "to_user": self.sarita.pk, "deactivate": True,
        }, format="json")
        self.assertEqual(r.status_code, 200)
        self.m_lead.refresh_from_db()
        self.mingma.refresh_from_db()
        self.assertEqual(self.m_lead.assigned_to, self.sarita)
        self.assertEqual(self.m_lead.next_follow_up, timezone.localdate())
        self.assertFalse(self.mingma.is_active)

    def test_handover_string_false_does_not_close_account(self):
        self.as_user(self.admin).post("/api/team/handover/", {
            "from_user": self.mingma.pk, "to_user": self.sarita.pk, "deactivate": "false",
        }, format="json")
        self.mingma.refresh_from_db()
        self.assertTrue(self.mingma.is_active)

    def test_handover_guards(self):
        c = self.as_user(self.admin)
        self.assertEqual(c.post("/api/team/handover/", {}, format="json").status_code, 400)
        self.assertEqual(c.post("/api/team/handover/", {
            "from_user": self.sarita.pk, "to_user": self.sarita.pk}, format="json").status_code, 400)
        self.assertEqual(c.post("/api/team/handover/", {
            "from_user": self.admin.pk, "to_user": self.sarita.pk, "deactivate": True,
        }, format="json").status_code, 400)

    def test_overdue_filter(self):
        stale = Lead.objects.create(full_name="Waiting", phone="9841000010",
                                    assigned_to=self.sarita)
        Lead.objects.filter(pk=stale.pk).update(created_at=timezone.now() - timedelta(hours=60))
        ids = [r["id"] for r in
               self.as_user(self.admin).get("/api/leads/?overdue=true").json()["results"]]
        self.assertIn(stale.pk, ids)
        self.assertEqual(self.as_user(self.admin).get("/api/dashboard/").json()["uncontacted"], 1)


# ---------------------------------------------------------------------------
# New features
# ---------------------------------------------------------------------------

import shutil  # noqa: E402
import tempfile  # noqa: E402
from datetime import datetime  # noqa: E402

from django.core import mail  # noqa: E402
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402
from rest_framework_simplejwt.tokens import AccessToken  # noqa: E402

from .models import Application, Course, Document, StatusChange, University  # noqa: E402


class StaffAddStudentTests(Base):
    def add(self, user, **extra):
        data = {"full_name": "Walk In", "phone": "9861 234567", "source": "walk-in",
                "consent_given": True, "interested_countries": [self.australia.pk]}
        data.update(extra)
        return self.as_user(user).post("/api/leads/", data, format="json")

    def test_counsellor_adds_walk_in_to_themselves(self):
        r = self.add(self.sarita, assigned_to=self.mingma.pk)
        self.assertEqual(r.status_code, 201, r.content)
        lead = Lead.objects.get(full_name="Walk In")
        self.assertEqual(lead.assigned_to, self.sarita)
        self.assertEqual(lead.created_by, self.sarita)
        self.assertEqual(lead.status, "contacted")
        self.assertEqual(lead.consent_method, "verbal")
        self.assertIsNotNone(lead.last_contacted_at)
        self.assertTrue(lead.notes.filter(body__contains="walk in").exists())

    def test_consent_and_source_are_required(self):
        self.assertEqual(self.add(self.sarita, consent_given=False).status_code, 400)
        self.assertEqual(self.add(self.sarita, source="made-up").status_code, 400)
        self.assertEqual(self.add(self.sarita, phone="12").status_code, 400)

    def test_duplicate_of_own_student_links_to_it(self):
        r = self.add(self.sarita, phone="+977 9841000001")
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json()["existing_id"], self.s_lead.pk)

    def test_duplicate_of_someone_elses_student_reveals_nothing(self):
        r = self.add(self.sarita, phone="9841000002")
        self.assertEqual(r.status_code, 409)
        self.assertNotIn("existing_id", r.json())
        self.assertNotIn("Bibek", r.content.decode())

    def test_owner_adds_and_assigns_with_email(self):
        self.mingma.email = "mingma@example.com"
        self.mingma.save()
        r = self.add(self.admin, assigned_to=self.mingma.pk)
        self.assertEqual(r.status_code, 201)
        lead = Lead.objects.get(full_name="Walk In")
        self.assertEqual(lead.assigned_to, self.mingma)
        self.assertTrue(Assignment.objects.filter(lead=lead, to_user=self.mingma).exists())
        self.assertEqual(mail.outbox[-1].to, ["mingma@example.com"])

    def test_owner_can_leave_unassigned_and_filter_for_it(self):
        self.add(self.admin)
        ids = [r["id"] for r in
               self.as_user(self.admin).get("/api/leads/?unassigned=true").json()["results"]]
        self.assertIn(Lead.objects.get(full_name="Walk In").pk, ids)

    def test_search_matches_phone_in_any_format(self):
        r = self.as_user(self.sarita).get("/api/leads/?search=+977 9841-000001").json()
        self.assertEqual([x["id"] for x in r["results"]], [self.s_lead.pk])


class AutoAssignTests(Base):
    def setUp(self):
        super().setUp()
        self.korea = Country.objects.create(name="South Korea", slug="south-korea")
        self.sarita.countries.set([self.australia])
        self.mingma.countries.set([self.korea])
        self.admin.email = "owner@example.com"
        self.admin.save()
        self.sarita.email = "sarita@example.com"
        self.sarita.save()

    def test_goes_to_country_specialist(self):
        self.intake(interested_countries=[self.australia.pk], email="ramesh@example.com")
        lead = Lead.objects.get(full_name="Ramesh")
        self.assertEqual(lead.assigned_to, self.sarita)
        self.assertTrue(Assignment.objects.filter(lead=lead, reason__startswith="Automatic"))
        recipients = [m.to for m in mail.outbox]
        self.assertIn(["owner@example.com", "sarita@example.com"], recipients)
        self.assertIn(["ramesh@example.com"], recipients)

    def test_no_country_goes_to_least_busy(self):
        Lead.objects.create(full_name="Extra", phone="9841000077", assigned_to=self.sarita)
        self.intake()
        self.assertEqual(Lead.objects.get(full_name="Ramesh").assigned_to, self.mingma)

    def test_opted_out_counsellors_are_skipped(self):
        self.sarita.auto_assign = False
        self.sarita.save()
        self.intake(interested_countries=[self.australia.pk])
        self.assertEqual(Lead.objects.get(full_name="Ramesh").assigned_to, self.mingma)

    @override_settings(AUTO_ASSIGN=False)
    def test_can_be_switched_off(self):
        self.intake(interested_countries=[self.australia.pk])
        self.assertIsNone(Lead.objects.get(full_name="Ramesh").assigned_to)


class ApplicationTests(Base):
    def setUp(self):
        super().setUp()
        self.uni = University.objects.create(country=self.australia, name="Deakin")
        self.other_uni = University.objects.create(country=self.australia, name="RMIT")
        self.course = Course.objects.create(university=self.uni, name="MIT", level="master")

    def test_counsellor_adds_application_without_commission(self):
        r = self.as_user(self.sarita).post(
            f"/api/leads/{self.s_lead.pk}/applications/",
            {"university": self.uni.pk, "course": self.course.pk, "status": "submitted",
             "commission_expected": "9999"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        app = Application.objects.get()
        self.assertIsNone(app.commission_expected)
        self.assertTrue(self.s_lead.notes.filter(body__contains="Deakin").exists())

    def test_owner_sets_commission_and_status_change_is_noted(self):
        c = self.as_user(self.admin)
        app_id = c.post(f"/api/leads/{self.s_lead.pk}/applications/",
                        {"university": self.uni.pk, "commission_expected": "2400"},
                        format="json").json()["id"]
        r = c.patch(f"/api/applications/{app_id}/", {"status": "offer_conditional"},
                    format="json")
        self.assertEqual(r.json()["status_display"], "Conditional offer")
        self.assertEqual(str(Application.objects.get().commission_expected), "2400.00")
        self.assertTrue(self.s_lead.notes.filter(body__contains="Conditional offer").exists())

    def test_course_must_match_university(self):
        r = self.as_user(self.sarita).post(
            f"/api/leads/{self.s_lead.pk}/applications/",
            {"university": self.other_uni.pk, "course": self.course.pk}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_other_counsellors_applications_are_out_of_reach(self):
        app = Application.objects.create(lead=self.m_lead, university=self.uni)
        c = self.as_user(self.sarita)
        self.assertEqual(c.post(f"/api/leads/{self.m_lead.pk}/applications/",
                                {"university": self.uni.pk}, format="json").status_code, 404)
        self.assertEqual(c.patch(f"/api/applications/{app.pk}/", {"status": "withdrawn"},
                                 format="json").status_code, 404)

    def test_university_options(self):
        r = self.as_user(self.sarita).get("/api/universities/").json()
        deakin = next(u for u in r if u["name"] == "Deakin")
        self.assertEqual(deakin["courses"], [{"id": self.course.pk, "name": "MIT"}])


class DocumentTests(Base):
    def setUp(self):
        super().setUp()
        self.media = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media)
        self.override.enable()

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media, ignore_errors=True)

    def upload(self, user, lead, name="passport.pdf", body=b"%PDF-1.4 test"):
        return self.as_user(user).post(
            f"/api/leads/{lead.pk}/documents/",
            {"doc_type": "passport", "file": SimpleUploadedFile(name, body)},
            format="multipart")

    def test_upload_and_download(self):
        r = self.upload(self.sarita, self.s_lead)
        self.assertEqual(r.status_code, 201, r.content)
        doc = Document.objects.get()
        self.assertNotIn("passport", doc.file.name)       # random stored name
        self.assertEqual(doc.original_name, "passport.pdf")
        r = self.as_user(self.sarita).get(f"/api/documents/{doc.pk}/download/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(b"".join(r.streaming_content), b"%PDF-1.4 test")

    def test_rejects_wrong_type_and_oversize(self):
        self.assertEqual(self.upload(self.sarita, self.s_lead, name="x.exe").status_code, 400)
        with override_settings(MAX_DOCUMENT_MB=0):
            self.assertEqual(self.upload(self.sarita, self.s_lead).status_code, 400)

    def test_other_counsellor_cannot_upload_download_or_delete(self):
        self.upload(self.mingma, self.m_lead)
        doc = Document.objects.get()
        c = self.as_user(self.sarita)
        self.assertEqual(self.upload(self.sarita, self.m_lead).status_code, 404)
        self.assertEqual(c.get(f"/api/documents/{doc.pk}/download/").status_code, 404)
        self.assertEqual(c.delete(f"/api/documents/{doc.pk}/").status_code, 404)

    def test_verified_documents_only_removed_by_owner(self):
        self.upload(self.sarita, self.s_lead)
        doc = Document.objects.get()
        self.as_user(self.sarita).patch(f"/api/documents/{doc.pk}/", {"is_verified": True},
                                        format="json")
        self.assertEqual(self.as_user(self.sarita).delete(f"/api/documents/{doc.pk}/").status_code, 403)
        self.assertEqual(self.as_user(self.admin).delete(f"/api/documents/{doc.pk}/").status_code, 204)
        self.assertFalse(Document.objects.exists())

    def test_no_public_media_url(self):
        self.upload(self.sarita, self.s_lead)
        doc = Document.objects.get()
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(f"/media/{doc.file.name}").status_code, 404)


class HistoryAndReportTests(Base):
    def test_stage_changes_are_recorded(self):
        self.as_user(self.sarita).patch(f"/api/leads/{self.s_lead.pk}/",
                                        {"status": "counselling"}, format="json")
        change = StatusChange.objects.get(lead=self.s_lead)
        self.assertEqual((change.from_status, change.to_status), ("contacted", "counselling"))
        detail = self.as_user(self.sarita).get(f"/api/leads/{self.s_lead.pk}/").json()
        self.assertEqual(detail["history"][0]["to_display"], "Counselling")

    def test_enrolled_this_year_uses_stage_date(self):
        self.as_user(self.admin).patch(f"/api/leads/{self.s_lead.pk}/",
                                       {"status": "enrolled"}, format="json")
        self.assertEqual(self.as_user(self.admin).get("/api/dashboard/").json()["enrolled_this_year"], 1)

    def test_report_date_range(self):
        Lead.objects.filter(pk=self.m_lead.pk).update(
            created_at=timezone.now() - timedelta(days=400))
        c = self.as_user(self.admin)
        this_year = timezone.localdate().replace(month=1, day=1)
        r = c.get(f"/api/reports/?from={this_year}").json()
        self.assertEqual(r["funnel"][0]["count"], 2)
        self.assertEqual(c.get("/api/reports/?from=yesterday").status_code, 400)
        self.assertEqual(c.get("/api/reports/?from=2026-02-01&to=2026-01-01").status_code, 400)

    def test_filtered_export_is_logged_and_excel_safe(self):
        r = self.as_user(self.admin).get("/api/leads/export/?status=contacted")
        body = r.content.decode("utf-8")
        self.assertTrue(body.startswith("\ufeff"))
        self.assertEqual(len(body.strip().splitlines()), 3)
        self.assertEqual(ExportLog.objects.get().filters, "status=contacted")


class AccountTests(Base):
    def test_password_change_signs_out_other_devices(self):
        other_device = AccessToken.for_user(self.sarita)
        other_device.set_iat(at_time=datetime.now() - timedelta(minutes=5))
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(self.sarita)}")
        r = c.post("/api/auth/password/", {"current_password": "pw-sarita-123",
                                           "new_password": "Pokhara-Lake-2026"}, format="json")
        self.assertEqual(r.status_code, 200)
        fresh = r.json()["access"]

        old = APIClient()
        old.credentials(HTTP_AUTHORIZATION=f"Bearer {other_device}")
        self.assertEqual(old.get("/api/leads/").status_code, 401)
        new = APIClient()
        new.credentials(HTTP_AUTHORIZATION=f"Bearer {fresh}")
        self.assertEqual(new.get("/api/leads/").status_code, 200)

    def test_createsuperuser_makes_an_owner(self):
        u = User.objects.create_superuser("boss", "boss@example.com", "Some-pass-123")
        self.assertEqual(u.role, "admin")
        self.assertFalse(u.must_change_password)


class MyAccountTests(Base):
    def test_update_profile_without_password(self):
        r = self.as_user(self.sarita).patch("/api/me/", {
            "first_name": "Sarita", "last_name": "Joshi", "email": "s@example.com",
            "bio": "Australia and UK.", "languages": "Nepali, English"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.sarita.refresh_from_db()
        self.assertEqual(self.sarita.email, "s@example.com")

    def test_username_change_needs_current_password(self):
        c = self.as_user(self.admin)
        self.assertEqual(c.patch("/api/me/", {"username": "puja"}, format="json").status_code, 400)
        self.assertEqual(c.patch("/api/me/", {"username": "puja", "current_password": "wrong"},
                                 format="json").status_code, 400)
        r = c.patch("/api/me/", {"username": "puja", "current_password": "pw-admin-123"},
                    format="json")
        self.assertEqual(r.json()["username"], "puja")
        self.assertEqual(self.client.post("/api/auth/login/", {"username": "puja",
                         "password": "pw-admin-123"}, format="json").status_code, 200)

    def test_username_must_be_unique_and_valid(self):
        c = self.as_user(self.admin)
        r = c.patch("/api/me/", {"username": "SARITA", "current_password": "pw-admin-123"},
                    format="json")
        self.assertEqual(r.status_code, 400)
        r = c.patch("/api/me/", {"username": "has space", "current_password": "pw-admin-123"},
                    format="json")
        self.assertEqual(r.status_code, 400)

    def test_cannot_promote_yourself(self):
        self.as_user(self.sarita).patch("/api/me/", {"role": "admin", "is_active": False,
                                                      "auto_assign": False}, format="json")
        self.sarita.refresh_from_db()
        self.assertEqual(self.sarita.role, "counsellor")
        self.assertTrue(self.sarita.is_active and self.sarita.auto_assign)

    def test_temporary_password_blocks_profile_changes(self):
        newbie = User.objects.create_user("newbie", password="Temp-pass-4821")
        r = self.as_user(newbie).patch("/api/me/", {"first_name": "X"}, format="json")
        self.assertEqual(r.status_code, 403)


class CommissionEditTests(Base):
    def test_only_owner_can_change_commission_later(self):
        uni = University.objects.create(country=self.australia, name="Deakin")
        app = Application.objects.create(lead=self.s_lead, university=uni)
        self.as_user(self.sarita).patch(f"/api/applications/{app.pk}/",
                                        {"commission_expected": "5000"}, format="json")
        app.refresh_from_db()
        self.assertIsNone(app.commission_expected)
        self.as_user(self.admin).patch(f"/api/applications/{app.pk}/",
                                       {"commission_expected": "2400"}, format="json")
        app.refresh_from_db()
        self.assertEqual(str(app.commission_expected), "2400.00")
        r = self.as_user(self.admin).get("/api/reports/").json()
        self.assertEqual(r["pipeline_value"], 0)          # still Draft: not counted
        self.as_user(self.admin).patch(f"/api/applications/{app.pk}/",
                                       {"status": "submitted"}, format="json")
        self.assertEqual(float(self.as_user(self.admin).get("/api/reports/").json()["pipeline_value"]), 2400)


class OwnerManagementTests(Base):
    """Staff and website content, managed from the staff area."""

    def test_counsellor_is_refused_everywhere(self):
        c = self.as_user(self.sarita)
        for path in ["/api/manage/staff/", "/api/manage/countries/", "/api/manage/universities/",
                     "/api/manage/courses/", "/api/manage/scholarships/", "/api/manage/batches/"]:
            self.assertEqual(c.get(path).status_code, 403, path)
            self.assertEqual(c.post(path, {}, format="json").status_code, 403, path)
        self.assertEqual(c.post(f"/api/manage/staff/{self.mingma.pk}/reset-password/",
                                {"password": "Whatever-123"}, format="json").status_code, 403)
        self.assertEqual(c.post(f"/api/leads/{self.s_lead.pk}/delete/",
                                {"confirm_name": "Anisha"}, format="json").status_code, 403)

    def test_add_counsellor_who_must_then_change_password(self):
        r = self.as_user(self.admin).post("/api/manage/staff/", {
            "username": "kiran", "first_name": "Kiran", "email": "k@example.com",
            "role": "counsellor", "password": "Temporary-Pass-77",
            "countries": [self.australia.pk], "auto_assign": True,
        }, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        kiran = User.objects.get(username="kiran")
        self.assertTrue(kiran.must_change_password)
        self.assertEqual(list(kiran.countries.all()), [self.australia])
        self.assertNotIn("password", r.json())
        login = self.client.post("/api/auth/login/", {"username": "kiran",
                                 "password": "Temporary-Pass-77"}, format="json")
        self.assertEqual(login.status_code, 200)

    def test_add_staff_validation(self):
        c = self.as_user(self.admin)
        self.assertEqual(c.post("/api/manage/staff/", {"username": "SARITA", "password": "Ok-Pass-12345"},
                                format="json").status_code, 400)
        self.assertEqual(c.post("/api/manage/staff/", {"username": "new1", "password": "123"},
                                format="json").status_code, 400)
        self.assertEqual(c.post("/api/manage/staff/", {"username": "new2"},
                                format="json").status_code, 400)

    def test_edit_countries_and_role(self):
        c = self.as_user(self.admin)
        r = c.patch(f"/api/manage/staff/{self.mingma.pk}/",
                    {"countries": [self.australia.pk], "auto_assign": False}, format="json")
        self.assertEqual(r.status_code, 200)
        self.mingma.refresh_from_db()
        self.assertFalse(self.mingma.auto_assign)
        r = c.patch(f"/api/manage/staff/{self.admin.pk}/", {"role": "counsellor"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_reset_password_forces_change_and_signs_out(self):
        c = self.as_user(self.admin)
        r = c.post(f"/api/manage/staff/{self.sarita.pk}/reset-password/",
                   {"password": "Fresh-Temp-2026"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.sarita.refresh_from_db()
        self.assertTrue(self.sarita.must_change_password)
        self.assertTrue(self.sarita.check_password("Fresh-Temp-2026"))
        self.assertIsNotNone(self.sarita.password_changed_at)
        self.assertEqual(c.post(f"/api/manage/staff/{self.admin.pk}/reset-password/",
                                {"password": "Fresh-Temp-2026"}, format="json").status_code, 400)

    def test_close_account_guards(self):
        c = self.as_user(self.admin)
        # Has open students: must use hand over
        r = c.post(f"/api/manage/staff/{self.sarita.pk}/deactivate/")
        self.assertEqual(r.status_code, 400)
        self.assertIn("Hand over", r.json()["detail"])
        self.assertEqual(c.post(f"/api/manage/staff/{self.admin.pk}/deactivate/").status_code, 400)
        Lead.objects.filter(assigned_to=self.mingma).update(status="lost")
        self.assertEqual(c.post(f"/api/manage/staff/{self.mingma.pk}/deactivate/").status_code, 200)
        self.mingma.refresh_from_db()
        self.assertFalse(self.mingma.is_active)
        self.assertEqual(c.post(f"/api/manage/staff/{self.mingma.pk}/reactivate/").status_code, 200)
        self.mingma.refresh_from_db()
        self.assertTrue(self.mingma.is_active)

    def test_content_crud_shows_on_public_site(self):
        c = self.as_user(self.admin)
        r = c.post("/api/manage/countries/", {"name": "New Zealand", "summary": "Kiwi.",
                                              "sort_order": 9}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        nz = r.json()
        self.assertEqual(nz["slug"], "new-zealand")
        uni = c.post("/api/manage/universities/", {"country": nz["id"], "name": "Otago",
                                                   "city": "Dunedin"}, format="json").json()
        c.post("/api/manage/courses/", {"university": uni["id"], "name": "MSc", "level": "master",
                                        "tuition_fee": "30000", "currency": "NZD"}, format="json")
        c.post(f"/api/manage/universities/{uni['id']}/mark-checked/")
        c.post("/api/manage/scholarships/", {"country": nz["id"], "name": "Kiwi award"},
               format="json")
        public = self.client.get("/api/countries/new-zealand/").json()
        self.assertEqual(public["universities"][0]["courses"][0]["currency"], "NZD")
        self.assertEqual(public["universities"][0]["last_verified_on"], str(timezone.localdate()))
        self.assertEqual(public["scholarships"][0]["name"], "Kiwi award")
        # Hide it
        c.patch(f"/api/manage/countries/{nz['id']}/", {"is_active": False}, format="json")
        self.assertEqual(self.client.get("/api/countries/new-zealand/").status_code, 404)

    def test_cannot_delete_content_students_depend_on(self):
        c = self.as_user(self.admin)
        self.s_lead.interested_countries.set([self.australia])
        self.assertEqual(c.delete(f"/api/manage/countries/{self.australia.pk}/").status_code, 400)
        uni = University.objects.create(country=self.australia, name="Deakin")
        Application.objects.create(lead=self.s_lead, university=uni)
        self.assertEqual(c.delete(f"/api/manage/universities/{uni.pk}/").status_code, 400)
        self.assertEqual(c.delete(f"/api/manage/countries/{self.hidden.pk}/").status_code, 204)

    def test_batches(self):
        c = self.as_user(self.admin)
        r = c.post("/api/manage/batches/", {"test_type": "ielts", "start_date":
                   str(timezone.localdate() + timedelta(days=5)), "total_seats": 20,
                   "seats_taken": 18}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(self.client.get("/api/batches/").json()[0]["seats_left"], 2)

    def test_delete_student_needs_exact_name(self):
        c = self.as_user(self.admin)
        self.assertEqual(c.post(f"/api/leads/{self.s_lead.pk}/delete/",
                                {"confirm_name": "anisha "}, format="json").status_code, 400)
        r = c.post(f"/api/leads/{self.s_lead.pk}/delete/", {"confirm_name": "Anisha"},
                   format="json")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Lead.objects.filter(pk=self.s_lead.pk).exists())


class SearchEngineTests(TestCase):
    def test_api_asks_search_engines_to_stay_out(self):
        r = self.client.get("/robots.txt")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Disallow: /", r.content.decode())
