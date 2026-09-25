"""
Browser tests for the four kinds of user: viewer, student, staff, admin.

Setup (fresh database, demo build):

    cd backend
    python manage.py flush --no-input && python manage.py seed_demo
    python manage.py shell -c "from core.models import Lead, User; [Lead.objects.create(full_name=f'Extra Student {i:02d}', phone=f'98410{i:05d}', consent_given=True, source='website') for i in range(20)]; User.objects.create_user('newbie', password='Temp-pass-4821', first_name='New', last_name='Hire')"
    python manage.py runserver        # CORS_ALLOWED_ORIGINS must include http://localhost:4173

    cd frontend
    VITE_DEMO_MODE=true npm run build && npx vite preview --port 4173

    pip install playwright && playwright install chromium
    python e2e/personas.py
"""
import os
import re
import tempfile

from playwright.sync_api import expect, sync_playwright

W = os.getenv("SITE_URL", "http://localhost:4173")
SHOTS = os.getenv("SHOTS_DIR", "e2e/screenshots")
os.makedirs(SHOTS, exist_ok=True)
results, console = [], []


def check(persona, name, fn):
    try:
        fn()
        results.append((persona, name, "PASS", ""))
    except Exception as e:  # noqa: BLE001
        msg = " | ".join(l.strip() for l in str(e).splitlines()[:3] if l.strip())[:220] or repr(e)
        results.append((persona, name, "FAIL", msg))


def rows(pg):
    return pg.locator("ul.divide-y > li")


with sync_playwright() as p:
    br = p.chromium.launch()

    def ctx(mobile=False):
        c = br.new_context(
            viewport={"width": 390, "height": 844} if mobile else {"width": 1280, "height": 900},
            accept_downloads=True,
        )
        pg = c.new_page()
        pg.on("pageerror", lambda e: console.append("PAGEERROR " + str(e)[:150]))
        pg.on("dialog", lambda d: d.accept())
        return c, pg

    def login(pg, user, pw="banana123"):
        pg.goto(W + "/staff/login")
        pg.fill("#u", user)
        pg.fill("#p", pw)
        pg.get_by_role("button", name="Sign in").click()
        pg.wait_for_url(W + "/staff", timeout=8000)

    # ================= VIEWER =================
    c, pg = ctx()

    def v_home_to_country():
        pg.goto(W + "/")
        pg.get_by_role("link", name=re.compile("^Australia")).click()
        pg.wait_for_url("**/study/australia")
        expect(pg.get_by_text("Deakin University").first).to_be_visible(timeout=8000)
        pg.screenshot(path=f"{SHOTS}/viewer_country.png", full_page=True)
    check("Viewer", "Home destination card opens the country page", v_home_to_country)

    def v_english_only():
        pg.goto(W + "/")
        assert pg.get_by_role("button", name="नेपालीमा हेर्नुहोस्").count() == 0
        pg.goto(W + "/apply?lang=ne")
        expect(pg.get_by_role("heading", name="Free counselling")).to_be_visible()
    check("Viewer", "English only (no language switch)", v_english_only)

    def v_privacy():
        pg.goto(W + "/privacy")
        expect(pg.get_by_role("heading", name="How we use your details")).to_be_visible()
        expect(pg.get_by_text("Template.")).to_be_visible()
    check("Viewer", "Privacy page (marked as template)", v_privacy)

    def v_404():
        pg.goto(W + "/nope")
        expect(pg.get_by_text("We couldn't find that page")).to_be_visible()
    check("Viewer", "404 page", v_404)

    for path in ["/staff", "/staff/new", "/staff/team", "/staff/reports", "/staff/leads/1"]:
        def v_guard(path=path):
            pg.goto(W + path)
            pg.wait_for_url("**/staff/login", timeout=5000)
        check("Viewer", f"{path} needs sign-in", v_guard)
    c.close()

    # ================= STUDENT (phone, QR link) =================
    c, pg = ctx(mobile=True)

    def s_errors():
        pg.goto(W + "/apply?src=fair-jan&country=1")
        expect(pg.get_by_role("heading", name="Free counselling")).to_be_visible()
        pg.get_by_role("button", name="Continue").click()
        expect(pg.get_by_text("This field may not be blank.").first).to_be_visible(timeout=5000)
        pg.screenshot(path=f"{SHOTS}/student_error.png", full_page=True)
    check("Student", "Empty form shows a clear message", s_errors)

    def s_submit():
        pg.fill("#name", "Ramesh Karki")
        pg.fill("#phone", "+977 9841 555 777")
        pg.locator("#consent").check()
        assert pg.get_by_role("button", name="Australia").get_attribute("aria-pressed") == "true"
        expect(pg.get_by_role("link", name="How we use your details")).to_be_visible()
        pg.get_by_role("button", name="Continue").click()
        expect(pg.get_by_text("A little more about you")).to_be_visible(timeout=5000)
        pg.select_option("#qual", "Bachelor's degree")
        pg.fill("#year", "2023")
        pg.select_option("#test", "ielts")
        pg.fill("#score", "6.5")
        pg.get_by_label("Yes, and it was refused").check()
        pg.fill("#refused-where", "Australia")
        pg.get_by_role("button", name="Finish").click()
        expect(pg.get_by_text("We have your details")).to_be_visible(timeout=5000)
        pg.screenshot(path=f"{SHOTS}/student_done.png", full_page=True)
    check("Student", "Two-step form completed on a phone", s_submit)
    c.close()

    # ================= STAFF (counsellor) =================
    c, pg = ctx()

    def st_auto_assigned():
        login(pg, "sarita")
        expect(pg.get_by_text("Your students, Sarita Joshi")).to_be_visible()
        assert pg.get_by_role("link", name="Team").count() == 0
        pg.get_by_role("button", name="Everyone").click()
        pg.wait_for_timeout(900)
        expect(pg.get_by_text("Ramesh Karki")).to_be_visible()
        assert rows(pg).count() == 5, f"expected 4 seeded + Ramesh, saw {rows(pg).count()}"
        assert pg.get_by_role("button", name="Unassigned").count() == 0
    check("Staff", "Australia student auto-assigned to Sarita; sees only own 5", st_auto_assigned)

    def st_add_walk_in():
        pg.get_by_role("link", name="+ Add student").click()
        pg.fill("#name", "Walk-in Wangchuk")
        pg.fill("#phone", "9801 234 567")
        pg.get_by_role("button", name="South Korea").click()
        pg.select_option("#source", "walk-in")
        pg.get_by_role("button", name="Add student").click()
        expect(pg.get_by_text(re.compile("agreed to be contacted"))).to_be_visible(timeout=5000)
        pg.get_by_label(re.compile("The student agreed")).check()
        pg.get_by_role("button", name="Add student").click()
        pg.wait_for_url(re.compile(r".*/staff/leads/\d+$"), timeout=6000)
        expect(pg.get_by_text("Added by Sarita Joshi (walk-in)")).to_be_visible()
        expect(pg.locator("dd", has_text="Agreed verbally to a counsellor")).to_be_visible()
        href = pg.get_by_role("link", name="WhatsApp").get_attribute("href")
        assert href == "https://wa.me/9779801234567", href
    check("Staff", "Adds a walk-in (consent required) + WhatsApp link", st_add_walk_in)

    def st_duplicate():
        pg.goto(W + "/staff/new")
        pg.fill("#name", "Same Person")
        pg.fill("#phone", "+977-9801234567")
        pg.get_by_label(re.compile("The student agreed")).check()
        pg.get_by_role("button", name="Add student").click()
        expect(pg.get_by_role("link", name="Open their record")).to_be_visible(timeout=5000)
        pg.get_by_role("link", name="Open their record").click()
        expect(pg.get_by_role("heading", name="Walk-in Wangchuk")).to_be_visible()
    check("Staff", "Duplicate number links to the existing student", st_duplicate)

    def st_application():
        pg.get_by_role("button", name="+ Add application").click()
        pg.select_option("#uni", label="Kyung Hee University")
        pg.wait_for_timeout(300)
        assert pg.locator("#app-commission").count() == 0, "commission field shown to counsellor"
        pg.select_option("#app-status", "submitted")
        pg.get_by_role("button", name="Save application").click()
        expect(pg.locator("li", has_text="Kyung Hee University")).to_be_visible(timeout=5000)
        pg.get_by_label("Stage for Kyung Hee University").select_option("offer_conditional")
        expect(pg.get_by_text(re.compile("Submitted → Conditional offer"))).to_be_visible(timeout=5000)
    check("Staff", "Adds an application and moves it to an offer", st_application)

    def st_documents():
        pdf = os.path.join(tempfile.mkdtemp(), "passport-scan.pdf")
        with open(pdf, "wb") as f:
            f.write(b"%PDF-1.4 test passport")
        pg.select_option("#doctype", "passport")
        pg.set_input_files("#docfile", pdf)
        pg.get_by_role("button", name="Upload").click()
        expect(pg.get_by_text("passport-scan.pdf")).to_be_visible(timeout=5000)
        with pg.expect_download() as d:
            pg.get_by_role("button", name="Download").click()
        assert open(d.value.path(), "rb").read() == b"%PDF-1.4 test passport"
        pg.get_by_role("button", name="Mark verified").click()
        expect(pg.get_by_text("· Verified")).to_be_visible(timeout=5000)
        assert pg.get_by_role("button", name="Delete").count() == 0, "counsellor can delete verified doc"
        pg.set_input_files("#docfile", {"name": "virus.exe", "mimeType": "application/octet-stream", "buffer": b"MZ"})
        pg.get_by_role("button", name="Upload").click()
        expect(pg.get_by_text("Upload a PDF, photo (JPG/PNG) or Word file.")).to_be_visible(timeout=5000)
        pg.screenshot(path=f"{SHOTS}/staff_lead_full.png", full_page=True)
    check("Staff", "Uploads, downloads and verifies a document; .exe refused", st_documents)

    def st_history():
        pg.select_option("#status", "docs_pending")
        pg.wait_for_timeout(700)
        pg.reload()
        expect(pg.get_by_text("Contacted → Documents pending")).to_be_visible(timeout=5000)
    check("Staff", "Stage history records the change", st_history)

    def st_other():
        pg.goto(W + "/staff/leads/8")
        expect(pg.get_by_text("This student isn't on your list")).to_be_visible(timeout=5000)
    check("Staff", "Another counsellor's student is refused", st_other)

    def st_newbie():
        c2 = br.new_context()
        p2 = c2.new_page()
        p2.goto(W + "/staff/login")
        p2.fill("#u", "newbie")
        p2.fill("#p", "Temp-pass-4821")
        p2.get_by_role("button", name="Sign in").click()
        p2.wait_for_url("**/staff/password", timeout=6000)
        p2.fill("#cur", "Temp-pass-4821")
        p2.fill("#new", "Kathmandu-River-77")
        p2.fill("#conf", "Kathmandu-River-77")
        p2.get_by_role("button", name="Save password").click()
        p2.wait_for_url(W + "/staff", timeout=6000)
        expect(p2.get_by_text("Your students, New Hire")).to_be_visible(timeout=5000)
        c2.close()
    check("Staff", "Temporary password → change → still signed in", st_newbie)
    c.close()

    # ================= ADMIN (owner) =================
    c, pg = ctx()

    def a_dashboard():
        login(pg, "admin")
        expect(pg.get_by_role("link", name="Reports")).to_be_visible()
        expect(pg.get_by_text("Waiting to be assigned")).to_be_visible()
        pg.get_by_role("button", name="Unassigned").click()
        pg.wait_for_timeout(900)
        expect(pg.get_by_text("Showing 25 of 23")).to_have_count(0)
        assert rows(pg).count() == 23, f"unassigned rows {rows(pg).count()}"
        pg.screenshot(path=f"{SHOTS}/admin_dashboard.png", full_page=True)
    check("Admin", "Dashboard + Unassigned tab (23)", a_dashboard)

    def a_student_detail():
        pg.get_by_role("button", name="Everyone").click()
        pg.wait_for_timeout(900)
        pg.get_by_text("Ramesh Karki").click()
        expect(pg.get_by_text("Previously refused a visa")).to_be_visible(timeout=5000)
        expect(pg.locator("dd", has_text="Ticked the box on the website")).to_be_visible()
        expect(pg.locator("#assign option", has_text="Mingma Sherpa")).to_have_count(1, timeout=5000)
        assert pg.locator("#assign").input_value() == "2", pg.locator("#assign").input_value()
        pg.select_option("#assign", label="Mingma Sherpa")
        pg.wait_for_timeout(800)
        assert pg.locator("#assign").input_value() == "3"
    check("Admin", "Sees the form answers; reassigns to Mingma", a_student_detail)

    def a_owner_add():
        pg.goto(W + "/staff/new")
        pg.fill("#name", "Referral Rai")
        pg.fill("#phone", "9812 000 111")
        pg.select_option("#source", "referral")
        pg.fill("#detail", "Referred by Deepa Magar")
        pg.select_option("#assign", label="Sarita Joshi")
        pg.get_by_label(re.compile("The student agreed")).check()
        pg.get_by_label("Signed a form").check()
        pg.get_by_role("button", name="Add student").click()
        pg.wait_for_url(re.compile(r".*/staff/leads/\d+$"), timeout=6000)
        expect(pg.locator("#assign option", has_text="Sarita Joshi")).to_have_count(1, timeout=5000)
        assert pg.locator("#assign").input_value() == "2", pg.locator("#assign").input_value()
        expect(pg.locator("dd", has_text="Signed a form in the office")).to_be_visible()
    check("Admin", "Adds a referral and assigns it to Sarita", a_owner_add)

    def a_commission():
        pg.get_by_role("button", name="+ Add application").click()
        pg.select_option("#uni", label="Deakin University")
        pg.fill("#app-commission", "2400")
        pg.get_by_role("button", name="Save application").click()
        expect(pg.get_by_text("$2,400")).to_be_visible(timeout=5000)
    check("Admin", "Owner records expected commission", a_commission)

    def a_team():
        pg.goto(W + "/staff/team")
        expect(pg.get_by_text(re.compile("Gets new website students · Australia"))).to_be_visible(timeout=5000)
        pg.screenshot(path=f"{SHOTS}/admin_team.png", full_page=True)
    check("Admin", "Team shows who receives which countries", a_team)

    def a_reports():
        pg.goto(W + "/staff/reports")
        expect(pg.get_by_text("Which sources produce students")).to_be_visible(timeout=5000)
        before = pg.locator("div.h-7 > div").first.inner_text()
        pg.fill("#from", "2099-01-01")
        pg.get_by_role("button", name="Show").click()
        pg.wait_for_timeout(900)
        assert pg.locator("div.h-7 > div").first.inner_text() == "0", "range not applied"
        pg.get_by_role("button", name="All time").click()
        pg.wait_for_timeout(900)
        assert pg.locator("div.h-7 > div").first.inner_text() == before
        pg.select_option("#exstatus", "contacted")
        with pg.expect_download() as d:
            pg.get_by_role("button", name="Download CSV").click()
        text = open(d.value.path(), encoding="utf-8-sig").read().strip().splitlines()
        assert len(text) > 1 and all(",Contacted," in r for r in text[1:]), text[:3]
        pg.screenshot(path=f"{SHOTS}/admin_reports.png", full_page=True)
    check("Admin", "Reports date range + filtered CSV export", a_reports)

    def a_switch_user():
        pg.goto(W + "/staff")
        pg.get_by_role("button", name="Sign out").click()
        pg.wait_for_url("**/staff/login")
        expect(pg.get_by_text("Demo accounts")).to_be_visible()
        login(pg, "mingma")
        assert pg.get_by_role("link", name="Team").count() == 0
        pg.get_by_role("button", name="Everyone").click()
        pg.wait_for_timeout(900)
        expect(pg.get_by_text("Ramesh Karki")).to_be_visible()
    check("Admin", "Mingma now sees Ramesh; owner links gone after switch", a_switch_user)
    c.close()
    br.close()

width = max(len(r[1]) for r in results)
for r in results:
    print(f"{r[2]}  {r[0]:8s} {r[1]:{width}s}  {r[3]}")
print(f"\n{sum(r[2] == 'PASS' for r in results)}/{len(results)} passed")
print("JavaScript errors:", len(console))
for m in sorted(set(console)):
    print("  ", m)
