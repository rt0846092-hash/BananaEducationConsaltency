"""
Banana Education Consultancy — core data model.

One Django app called `core` holds everything. For a solo developer this is
much easier to reason about than three separate apps.

In settings.py you must add:
    AUTH_USER_MODEL = "core.User"

And your MySQL database MUST use utf8mb4, not utf8. MySQL's "utf8" is a
3-byte charset that silently breaks on some Korean, Nepali and Bengali
characters. In settings.py:

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": "banana",
            "OPTIONS": {"charset": "utf8mb4"},
        }
    }
"""

import os
import uuid

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.utils import timezone


def phone_key(value):
    """Last ten digits, so '+977 9851 111222' and '9851111222' compare equal."""
    return "".join(c for c in (value or "") if c.isdigit())[-10:]


class StaffManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        # `createsuperuser` used to produce a *counsellor* who could not see
        # reports and was blocked until changing a password they just chose.
        extra_fields.setdefault("role", "admin")
        extra_fields.setdefault("must_change_password", False)
        return super().create_superuser(username, email, password, **extra_fields)


# ---------------------------------------------------------------------------
# People who log in
# ---------------------------------------------------------------------------

class User(AbstractUser):
    """Staff accounts. Students never log in, so they are NOT users."""

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        COUNSELLOR = "counsellor", "Counsellor"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.COUNSELLOR)
    phone = models.CharField(max_length=30, blank=True)
    photo_url = models.URLField(blank=True)
    bio = models.TextField(blank=True)
    languages = models.CharField(max_length=200, blank=True, help_text="Comma separated")
    is_public = models.BooleanField(default=True, help_text="Show on the public counsellors page")

    # Defaults to True so every account created by hand starts with a password
    # the owner chose and the staff member must replace. Until they do, the
    # owner knows their password, which would let anyone dispute an entry in
    # the call log or the handover history.
    must_change_password = models.BooleanField(
        default=True, help_text="Force a new password at next sign in"
    )

    # Automatic assignment of students from the public form.
    countries = models.ManyToManyField(
        "Country", blank=True, related_name="specialists",
        help_text="Destinations this counsellor handles. New students interested in "
                  "these countries go to them first.",
    )
    auto_assign = models.BooleanField(
        default=True, help_text="Receive new students from the website automatically",
    )

    # Every sign-in token issued before this moment stops working, so changing
    # a password (or having it reset) signs out every other device.
    password_changed_at = models.DateTimeField(null=True, blank=True, editable=False)

    objects = StaffManager()

    def set_password(self, raw_password):
        super().set_password(raw_password)
        self.password_changed_at = timezone.now()

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    def __str__(self):
        return self.get_full_name() or self.username


# ---------------------------------------------------------------------------
# Public catalogue content
# ---------------------------------------------------------------------------

class Country(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(unique=True)
    summary = models.TextField(blank=True)
    visa_notes = models.TextField(blank=True)
    hero_image_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "countries"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class University(models.Model):
    country = models.ForeignKey(Country, on_delete=models.PROTECT, related_name="universities")
    name = models.CharField(max_length=200)
    city = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    description = models.TextField(blank=True)
    logo_url = models.URLField(blank=True)
    is_partner = models.BooleanField(default=False, help_text="We earn commission here")
    is_active = models.BooleanField(default=True)

    # Tuition and deadlines go stale fast and families make expensive
    # decisions on them. Show this date on the public page.
    last_verified_on = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("country", "name")]

    def __str__(self):
        return f"{self.name} ({self.country.name})"


class Course(models.Model):
    """Fees are quoted per course, not per university."""

    class Level(models.TextChoices):
        FOUNDATION = "foundation", "Foundation"
        DIPLOMA = "diploma", "Diploma"
        BACHELOR = "bachelor", "Bachelor"
        MASTER = "master", "Master"
        PHD = "phd", "PhD"

    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name="courses")
    name = models.CharField(max_length=200)
    level = models.CharField(max_length=20, choices=Level.choices)
    duration_months = models.PositiveIntegerField(null=True, blank=True)
    tuition_fee = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="USD")
    intake_months = models.CharField(max_length=100, blank=True, help_text="e.g. Jan, May, Sep")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["university", "name"]

    def __str__(self):
        return f"{self.name} — {self.university.name}"


class Scholarship(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="scholarships")
    university = models.ForeignKey(
        University, on_delete=models.CASCADE, related_name="scholarships", null=True, blank=True
    )
    name = models.CharField(max_length=200)
    amount_note = models.CharField(max_length=200, blank=True, help_text="e.g. Up to 50% tuition")
    eligibility = models.TextField(blank=True)
    deadline = models.DateField(null=True, blank=True)
    link = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["deadline", "name"]

    def __str__(self):
        return self.name


class TestPrepBatch(models.Model):
    """IELTS / PTE / TOEFL / TOPIK classes. A start date creates urgency
    on the public page in a way a price list never does."""

    class TestType(models.TextChoices):
        IELTS = "ielts", "IELTS"
        PTE = "pte", "PTE"
        TOEFL = "toefl", "TOEFL"
        TOPIK = "topik", "TOPIK"
        OTHER = "other", "Other"

    test_type = models.CharField(max_length=20, choices=TestType.choices)
    title = models.CharField(max_length=150, blank=True)
    start_date = models.DateField()
    schedule_note = models.CharField(max_length=200, blank=True, help_text="e.g. Sun–Thu, 7–9 am")
    duration_weeks = models.PositiveIntegerField(null=True, blank=True)
    fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_seats = models.PositiveIntegerField(default=20)
    seats_taken = models.PositiveIntegerField(default=0)
    instructor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["start_date"]

    @property
    def seats_left(self):
        return max(self.total_seats - self.seats_taken, 0)

    def __str__(self):
        return f"{self.get_test_type_display()} — {self.start_date}"


# ---------------------------------------------------------------------------
# The part that earns money
# ---------------------------------------------------------------------------

class Lead(models.Model):
    """A student. Created by the QR intake form. Never deleted, only closed."""

    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        COUNSELLING = "counselling", "Counselling"
        DOCS_PENDING = "docs_pending", "Documents pending"
        APPLIED = "applied", "Applied"
        OFFER = "offer", "Offer received"
        VISA_FILED = "visa_filed", "Visa filed"
        ENROLLED = "enrolled", "Enrolled"
        LOST = "lost", "Lost"

    class VisaHistory(models.TextChoices):
        NONE = "none", "Never applied"
        APPROVED = "approved", "Applied and approved"
        REFUSED = "refused", "Applied and refused"

    class TestType(models.TextChoices):
        NONE = "none", "No test yet"
        IELTS = "ielts", "IELTS"
        PTE = "pte", "PTE"
        TOEFL = "toefl", "TOEFL"
        TOPIK = "topik", "TOPIK"

    # --- step 1 of the form: saved immediately, before anything else ---
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30, db_index=True)
    # Digits only, filled in on save. Lets the duplicate check run in the
    # database instead of comparing every phone number in Python.
    phone_key = models.CharField(max_length=10, blank=True, db_index=True, editable=False)
    email = models.EmailField(blank=True)
    interested_countries = models.ManyToManyField(Country, related_name="leads", blank=True)

    # --- step 2: all optional ---
    highest_qualification = models.CharField(max_length=120, blank=True)
    completion_year = models.PositiveIntegerField(null=True, blank=True)
    study_gap_years = models.PositiveIntegerField(null=True, blank=True)
    test_type = models.CharField(max_length=20, choices=TestType.choices, default=TestType.NONE)
    test_score = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    test_date = models.DateField(null=True, blank=True)
    budget_note = models.CharField(max_length=120, blank=True)
    target_intake = models.CharField(max_length=60, blank=True, help_text="e.g. Sep 2026")

    # Asked as "have you applied for a student visa before?" — never as
    # "were you rejected?". People find that accusatory and either lie or leave.
    visa_history = models.CharField(
        max_length=20, choices=VisaHistory.choices, default=VisaHistory.NONE
    )
    visa_history_country = models.CharField(max_length=80, blank=True)
    visa_history_date = models.DateField(null=True, blank=True)

    message = models.TextField(blank=True)

    # --- where this lead came from: ?src=fair-jan on the QR link ---
    source = models.CharField(max_length=60, blank=True, db_index=True)
    source_detail = models.CharField(max_length=200, blank=True)

    # --- pipeline ---
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.NEW, db_index=True
    )
    assigned_to = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="leads", db_index=True,
    )
    last_contacted_at = models.DateTimeField(null=True, blank=True)
    next_follow_up = models.DateField(null=True, blank=True, db_index=True)
    lost_reason = models.CharField(max_length=200, blank=True)

    # --- consent: we collect phone numbers, education and visa history ---
    class ConsentMethod(models.TextChoices):
        FORM = "form", "Ticked the box on the website"
        VERBAL = "verbal", "Agreed verbally to a counsellor"
        WRITTEN = "written", "Signed a form in the office"

    consent_given = models.BooleanField(default=False)
    consent_at = models.DateTimeField(null=True, blank=True)
    consent_method = models.CharField(
        max_length=20, choices=ConsentMethod.choices, default=ConsentMethod.FORM
    )

    # Null means the student filled in the public form themselves.
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="leads_added",
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "assigned_to"])]

    def save(self, *args, **kwargs):
        self.phone_key = phone_key(self.phone)
        if kwargs.get("update_fields") is not None and "phone" in kwargs["update_fields"]:
            kwargs["update_fields"] = list(set(kwargs["update_fields"]) | {"phone_key"})
        super().save(*args, **kwargs)

    @property
    def hours_since_created(self):
        return (timezone.now() - self.created_at).total_seconds() / 3600

    @property
    def is_overdue(self):
        """Powers the one number the owner logs in to see."""
        if self.status in (self.Status.ENROLLED, self.Status.LOST):
            return False
        if self.last_contacted_at is None:
            return self.hours_since_created > 48
        return bool(self.next_follow_up and self.next_follow_up < timezone.localdate())

    def __str__(self):
        return f"{self.full_name} ({self.phone})"


class Application(models.Model):
    """One student applies to several universities. This is where commission
    is tracked, so it cannot live on the Lead."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        OFFER_CONDITIONAL = "offer_conditional", "Conditional offer"
        OFFER_UNCONDITIONAL = "offer_unconditional", "Unconditional offer"
        REJECTED = "rejected", "Rejected by university"
        VISA_FILED = "visa_filed", "Visa filed"
        VISA_APPROVED = "visa_approved", "Visa approved"
        VISA_REFUSED = "visa_refused", "Visa refused"
        ENROLLED = "enrolled", "Enrolled"
        WITHDRAWN = "withdrawn", "Withdrawn"

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="applications")
    university = models.ForeignKey(University, on_delete=models.PROTECT)
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True)
    intake = models.CharField(max_length=60, blank=True, help_text="e.g. Sep 2026")
    deadline = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT)
    commission_expected = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["deadline", "-created_at"]

    def __str__(self):
        return f"{self.lead.full_name} → {self.university.name}"


class Note(models.Model):
    """Every phone call gets logged here. Append only — never edited."""

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    body = models.TextField()
    is_call_log = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Note on {self.lead.full_name} at {self.created_at:%Y-%m-%d}"


def document_path(instance, filename):
    """Random names. A passport saved as 'passport.pdf' under a date folder is
    guessable; a UUID is not. Files are only ever served through the API."""
    ext = os.path.splitext(filename)[1].lower()[:10]
    return f"documents/{instance.lead_id}/{uuid.uuid4().hex}{ext}"


class Document(models.Model):
    class DocType(models.TextChoices):
        PASSPORT = "passport", "Passport"
        TRANSCRIPT = "transcript", "Academic transcript"
        CERTIFICATE = "certificate", "Certificate"
        TEST_SCORE = "test_score", "Test score report"
        BANK_STATEMENT = "bank_statement", "Bank statement"
        SPONSOR = "sponsor", "Sponsor documents"
        SOP = "sop", "Statement of purpose"
        OTHER = "other", "Other"

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="documents")
    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="documents", null=True, blank=True
    )
    doc_type = models.CharField(max_length=30, choices=DocType.choices)
    file = models.FileField(upload_to=document_path, max_length=255)
    original_name = models.CharField(max_length=200, blank=True)
    is_verified = models.BooleanField(default=False)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_doc_type_display()} — {self.lead.full_name}"


class StatusChange(models.Model):
    """Every move through the pipeline, so 'when did this go cold?' has an answer."""

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="status_changes")
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.lead.full_name}: {self.from_status or '—'} → {self.to_status}"


class Assignment(models.Model):
    """Handover log. A two-person office never touches this. A ten-person
    office lives in it, and it answers 'whose hands was this in?'."""

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="assignments")
    from_user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="handovers_given"
    )
    to_user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="handovers_received"
    )
    changed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="handovers_made"
    )
    reason = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.lead.full_name}: {self.from_user} → {self.to_user}"


class ExportLog(models.Model):
    """Lead lists are the consultancy's most valuable asset. Only admins can
    export, and every export is recorded. This is a selling point, not a
    technical detail."""

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    row_count = models.PositiveIntegerField()
    filters = models.CharField(max_length=300, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]