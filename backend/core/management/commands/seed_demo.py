"""
Fills an empty database with believable demo content.

    python manage.py seed_demo

Everything here is sample data for a fictional consultancy. Fees and deadlines
are made up. Never ship invented numbers on a real client's site — families
make expensive decisions on them.
"""

import os
import random
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import (
    Application, Country, Course, Lead, Note, Scholarship, StatusChange, TestPrepBatch,
    University, User,
)

COUNTRIES = [
    ("Australia", "australia", "Post-study work rights of two to four years and a large "
     "network of partner institutions. February and July intakes.",
     "Genuine Student requirement replaced the old GTE in 2024. Financial evidence must "
     "cover first-year tuition, living costs and travel."),
    ("United States", "usa", "The widest range of programmes and the largest pool of "
     "university-funded scholarships. Fall and Spring intakes.",
     "F-1 visa. Interview at the embassy, SEVIS fee paid before booking."),
    ("United Kingdom", "uk", "One-year master's degrees and a two-year Graduate Route "
     "after finishing. September and January intakes.",
     "Student route visa with CAS from the university. Maintenance funds held 28 days."),
    ("South Korea", "south-korea", "Low tuition compared to the West, strong engineering "
     "and design programmes, and TOPIK-based scholarships. March and September intakes.",
     "D-2 study visa. Most universities ask for TOPIK level 3 for Korean-taught degrees; "
     "English-taught tracks accept IELTS instead."),
    ("Europe", "europe", "Low or no tuition in Germany and the Nordics, with a growing "
     "number of English-taught master's programmes.",
     "Requirements vary by country. Germany asks for a blocked account; the Netherlands "
     "and Ireland do not."),
]

UNIVERSITIES = {
    "australia": [
        ("Deakin University", "Melbourne", True),
        ("Griffith University", "Brisbane", True),
        ("University of Wollongong", "Wollongong", True),
        ("RMIT University", "Melbourne", False),
    ],
    "usa": [
        ("Arizona State University", "Tempe", True),
        ("University of Illinois Chicago", "Chicago", False),
        ("Northeastern University", "Boston", True),
    ],
    "uk": [
        ("University of Greenwich", "London", True),
        ("Coventry University", "Coventry", True),
        ("University of Leeds", "Leeds", False),
    ],
    "south-korea": [
        ("Yonsei University", "Seoul", False),
        ("Pusan National University", "Busan", True),
        ("Kyung Hee University", "Seoul", True),
    ],
    "europe": [
        ("TU Berlin", "Berlin", False),
        ("University of Twente", "Enschede", True),
    ],
}

COURSES = [
    ("Master of Information Technology", "master", 24, 32000, "USD"),
    ("Master of Business Administration", "master", 18, 38000, "USD"),
    ("Bachelor of Nursing", "bachelor", 36, 28000, "USD"),
    ("Master of Data Science", "master", 24, 35000, "USD"),
    ("Bachelor of Civil Engineering", "bachelor", 48, 26000, "USD"),
]

STUDENTS = [
    ("Anisha Gurung", "+977 9841 220145", "counselling"),
    ("Rajesh Tamang", "+977 9803 771290", "new"),
    ("Sabina Karki", "+977 9860 114872", "docs_pending"),
    ("Bibek Shrestha", "+977 9812 664301", "applied"),
    ("Priyanka Rai", "+977 9845 903318", "new"),
    ("Sujan Adhikari", "+977 9808 445127", "offer"),
    ("Manisha Thapa", "+977 9851 337604", "contacted"),
    ("Kiran Bhattarai", "+977 9823 550918", "visa_filed"),
    ("Deepa Magar", "+977 9861 782240", "enrolled"),
    ("Nabin Poudel", "+977 9814 006553", "lost"),
    ("Sneha Maharjan", "+977 9849 118837", "new"),
    ("Aayush Lamichhane", "+977 9807 992146", "counselling"),
]

SOURCES = ["office-door", "fair-jan", "brochure", "instagram", "website", "referral"]


class Command(BaseCommand):
    help = "Load sample content and students for the demo"

    def handle(self, *args, **options):
        if Country.objects.exists():
            self.stdout.write(self.style.WARNING("Data already present — nothing to do."))
            return

        random.seed(7)
        today = timezone.localdate()

        # A demo on a laptop gets the easy password from the README. Anywhere
        # else (DEBUG off) each account gets its own random password, printed
        # once, and must replace it at first sign-in. Set DEMO_PASSWORD to
        # choose one yourself, e.g. for a public demo you'll reset later.
        chosen = os.getenv("DEMO_PASSWORD") or ("banana123" if settings.DEBUG else None)
        passwords = {}

        def password_for(username):
            passwords[username] = chosen or secrets.token_urlsafe(9)
            return passwords[username]

        must_change = chosen is None

        admin = User.objects.create_superuser(
            username="admin", password=password_for("admin"), email="owner@banana.demo",
            first_name="Puja", last_name="Rana", role=User.Role.ADMIN,
            bio="Founder. Fifteen years placing students in Australia and the UK.",
            languages="Nepali, English, Hindi",
            must_change_password=must_change,
        )

        counsellors = [
            User.objects.create_user(
                username="sarita", password=password_for("sarita"), first_name="Sarita",
                last_name="Joshi", role=User.Role.COUNSELLOR,
                bio="Handles Australia and the UK. Former visa documentation officer.",
                languages="Nepali, English",
                must_change_password=must_change,
            ),
            User.objects.create_user(
                username="mingma", password=password_for("mingma"), first_name="Mingma",
                last_name="Sherpa", role=User.Role.COUNSELLOR,
                bio="Handles South Korea and Europe. Studied in Busan for three years.",
                languages="Nepali, English, Korean",
                must_change_password=must_change,
            ),
        ]

        for order, (name, slug, summary, visa) in enumerate(COUNTRIES):
            country = Country.objects.create(
                name=name, slug=slug, summary=summary, visa_notes=visa, sort_order=order
            )
            for uni_name, city, partner in UNIVERSITIES[slug]:
                uni = University.objects.create(
                    country=country, name=uni_name, city=city, is_partner=partner,
                    last_verified_on=today - timedelta(days=random.randint(3, 40)),
                    description=f"Sample entry for the demo. Confirm all figures with "
                                f"{uni_name} directly before applying.",
                )
                for course_name, level, months, fee, currency in random.sample(COURSES, 3):
                    Course.objects.create(
                        university=uni, name=course_name, level=level,
                        duration_months=months, tuition_fee=fee, currency=currency,
                        intake_months="Feb, Jul" if slug == "australia" else "Jan, Sep",
                    )

            Scholarship.objects.create(
                country=country,
                name=f"{name} merit award for international students",
                amount_note="Up to 30% of tuition",
                eligibility="Sample criteria for the demo. Typically a strong academic "
                            "record and an English test score above the minimum.",
                deadline=today + timedelta(days=random.randint(30, 120)),
            )

        for i, (test, weeks, fee) in enumerate([
            ("ielts", 6, 12000), ("pte", 4, 10000), ("topik", 8, 15000), ("ielts", 6, 12000),
        ]):
            TestPrepBatch.objects.create(
                test_type=test,
                start_date=today + timedelta(days=7 + i * 14),
                schedule_note=random.choice(["Sun–Thu, 7–9 am", "Sun–Thu, 5–7 pm",
                                             "Fri & Sat, 10 am–1 pm"]),
                duration_weeks=weeks, fee=fee, total_seats=20,
                seats_taken=random.randint(8, 18),
                instructor=random.choice(counsellors),
            )

        # Who handles which destinations, for automatic assignment.
        by_slug = {c.slug: c for c in Country.objects.all()}
        counsellors[0].countries.set([by_slug["australia"], by_slug["uk"]])
        counsellors[1].countries.set([by_slug["south-korea"], by_slug["europe"]])

        countries = list(Country.objects.all())
        universities = list(University.objects.all())

        for i, (name, phone, lead_status) in enumerate(STUDENTS):
            created = timezone.now() - timedelta(days=random.randint(0, 45),
                                                 hours=random.randint(0, 20))
            contacted = None
            if lead_status != "new":
                contacted = created + timedelta(hours=random.randint(2, 30))

            lead = Lead.objects.create(
                full_name=name, phone=phone,
                email=f"{name.split()[0].lower()}@example.com" if i % 3 else "",
                status=lead_status,
                source=random.choice(SOURCES),
                assigned_to=None if lead_status == "new" else random.choice(counsellors),
                highest_qualification=random.choice([
                    "+2 Science", "Bachelor of Business Studies", "BSc Computer Science",
                    "Diploma in Civil Engineering", "+2 Management",
                ]),
                completion_year=random.randint(2019, 2025),
                study_gap_years=random.randint(0, 3),
                test_type=random.choice(["ielts", "pte", "none", "ielts", "topik"]),
                test_score=random.choice([6.0, 6.5, 7.0, None]),
                target_intake=random.choice(["Sep 2026", "Jan 2027", "Feb 2027"]),
                visa_history=random.choice(["none", "none", "none", "refused", "approved"]),
                budget_note=random.choice(["Up to 30 lakh", "Family sponsor", "Bank loan"]),
                consent_given=True, consent_at=created,
                last_contacted_at=contacted,
                next_follow_up=today + timedelta(days=random.randint(-4, 10))
                if lead_status not in ("new", "enrolled", "lost") else None,
            )
            Lead.objects.filter(pk=lead.pk).update(created_at=created)
            StatusChange.objects.create(lead=lead, to_status=lead_status,
                                        changed_by=lead.assigned_to)
            lead.interested_countries.set(random.sample(countries, random.randint(1, 2)))

            if lead.visa_history == "refused":
                lead.visa_history_country = "Australia"
                lead.visa_history_date = today - timedelta(days=random.randint(200, 600))
                lead.save(update_fields=["visa_history_country", "visa_history_date"])

            if contacted:
                Note.objects.create(
                    lead=lead, author=lead.assigned_to, is_call_log=True,
                    body=random.choice([
                        "Called and explained the intake timeline. Sending the document "
                        "checklist on WhatsApp.",
                        "Spoke with the father. Funds are ready but the bank statement is "
                        "only two months old — needs six.",
                        "Wants Australia, but the gap is four years. Suggested a diploma "
                        "pathway instead of direct entry to master's.",
                        "Booked an office visit for Saturday morning.",
                    ]),
                )

            if lead_status in ("applied", "offer", "visa_filed", "enrolled"):
                Application.objects.create(
                    lead=lead, university=random.choice(universities),
                    intake=lead.target_intake,
                    deadline=today + timedelta(days=random.randint(20, 90)),
                    status={"applied": "submitted", "offer": "offer_conditional",
                            "visa_filed": "visa_filed", "enrolled": "enrolled"}[lead_status],
                    commission_expected=random.choice([1800, 2400, 3000]),
                )

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {Lead.objects.count()} students, {University.objects.count()} "
            f"universities, {TestPrepBatch.objects.count()} classes.\n"
        ))
        for username, pw in passwords.items():
            self.stdout.write(f"  {username:8s} {pw}")
        if must_change:
            self.stdout.write(self.style.WARNING(
                "These passwords are shown once. Each person must choose their own "
                "at first sign-in."
            ))
        _ = admin