import os

from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from .models import (
    Application, Country, Course, Document, Lead, Note, Scholarship, StatusChange,
    TestPrepBatch, University, User, phone_key,  # noqa: F401 — re-exported for views
)


# ---------------------------------------------------------------------------
# Public read-only content
# ---------------------------------------------------------------------------

class CourseSerializer(serializers.ModelSerializer):
    level_display = serializers.CharField(source="get_level_display", read_only=True)

    class Meta:
        model = Course
        fields = ["id", "name", "level", "level_display", "duration_months",
                  "tuition_fee", "currency", "intake_months"]


class UniversitySerializer(serializers.ModelSerializer):
    courses = CourseSerializer(many=True, read_only=True)

    class Meta:
        model = University
        fields = ["id", "name", "city", "website", "description", "logo_url",
                  "is_partner", "last_verified_on", "courses"]


class ScholarshipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scholarship
        fields = ["id", "name", "amount_note", "eligibility", "deadline", "link"]


class CountryListSerializer(serializers.ModelSerializer):
    university_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Country
        fields = ["id", "name", "slug", "summary", "hero_image_url", "university_count"]


class CountryDetailSerializer(serializers.ModelSerializer):
    universities = serializers.SerializerMethodField()
    scholarships = serializers.SerializerMethodField()

    class Meta:
        model = Country
        fields = ["id", "name", "slug", "summary", "visa_notes", "hero_image_url",
                  "universities", "scholarships"]

    def get_universities(self, obj):
        qs = obj.universities.filter(is_active=True).prefetch_related("courses")
        return UniversitySerializer(qs, many=True).data

    def get_scholarships(self, obj):
        return ScholarshipSerializer(obj.scholarships.filter(is_active=True), many=True).data


class BatchSerializer(serializers.ModelSerializer):
    test_type_display = serializers.CharField(source="get_test_type_display", read_only=True)
    seats_left = serializers.IntegerField(read_only=True)

    class Meta:
        model = TestPrepBatch
        fields = ["id", "test_type", "test_type_display", "title", "start_date",
                  "schedule_note", "duration_weeks", "fee", "seats_left"]


class AccountSerializer(serializers.ModelSerializer):
    """What a signed-in person can change about themselves in the staff area.

    Role, active status and auto-assignment stay with the owner — nobody
    promotes themselves. A new username needs the current password, so a
    colleague at an unlocked computer can't quietly take over the account.
    """

    current_password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    is_public = serializers.BooleanField(required=False)

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "phone", "bio",
                  "languages", "is_public", "current_password"]

    def validate_username(self, value):
        value = value.strip()
        taken = User.objects.filter(username__iexact=value).exclude(pk=self.instance.pk)
        if taken.exists():
            raise serializers.ValidationError("Someone already uses that username.")
        return value

    def validate(self, attrs):
        new = attrs.get("username")
        if new is not None and new != self.instance.username:
            if not self.instance.check_password(attrs.get("current_password") or ""):
                raise serializers.ValidationError(
                    {"current_password": "Enter your current password to change your username."}
                )
        attrs.pop("current_password", None)
        return attrs


class CounsellorSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "name", "bio", "photo_url", "languages"]

    def get_name(self, obj):
        return obj.get_full_name() or obj.username


# ---------------------------------------------------------------------------
# The public intake form
# ---------------------------------------------------------------------------

def clean_phone(value):
    """Shared by the public form and staff edits so a number stays callable."""
    digits = "".join(c for c in value if c.isdigit())
    if len(digits) < 7:
        raise serializers.ValidationError("Enter a phone number we can call you on.")
    return value.strip()


class IntakeStepOneSerializer(serializers.ModelSerializer):
    """Three fields. Saved the instant they are submitted, before the student
    sees step two, so an abandoned form still leaves a callable phone number."""

    # A hidden field no human ever fills in. Bots fill everything, so anything
    # arriving with a value here is discarded.
    website = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = Lead
        fields = ["id", "full_name", "phone", "email", "interested_countries",
                  "source", "source_detail", "consent_given", "website"]
        extra_kwargs = {"consent_given": {"required": True}}

    def validate_consent_given(self, value):
        if not value:
            raise serializers.ValidationError("Tick the box to let us contact you.")
        return value

    def validate_phone(self, value):
        return clean_phone(value)

    def create(self, validated_data):
        validated_data.pop("website", None)
        countries = validated_data.pop("interested_countries", [])
        validated_data["consent_at"] = timezone.now()
        lead = Lead.objects.create(**validated_data)
        lead.interested_countries.set(countries)
        return lead


class IntakeStepTwoSerializer(serializers.ModelSerializer):
    """Everything here is optional. If the student stops, we already have
    what matters."""

    class Meta:
        model = Lead
        fields = ["highest_qualification", "completion_year", "study_gap_years",
                  "test_type", "test_score", "test_date", "budget_note",
                  "target_intake", "visa_history", "visa_history_country",
                  "visa_history_date", "message"]


# ---------------------------------------------------------------------------
# Staff views of a lead
# ---------------------------------------------------------------------------

class NoteSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = Note
        fields = ["id", "body", "is_call_log", "author_name", "created_at"]
        read_only_fields = ["author_name", "created_at"]

    def get_author_name(self, obj):
        return obj.author.get_full_name() if obj.author else "Removed user"


class ApplicationSerializer(serializers.ModelSerializer):
    university_name = serializers.CharField(source="university.name", read_only=True)
    country_name = serializers.CharField(source="university.country.name", read_only=True)
    course_name = serializers.CharField(source="course.name", read_only=True, default="")
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Application
        fields = ["id", "university", "university_name", "country_name", "course",
                  "course_name", "intake", "deadline", "status", "status_display",
                  "commission_expected", "notes"]

    def validate(self, attrs):
        university = attrs.get("university") or getattr(self.instance, "university", None)
        course = attrs.get("course")
        if course and university and course.university_id != university.pk:
            raise serializers.ValidationError({"course": "That course isn't at this university."})
        return attrs


class DocumentSerializer(serializers.ModelSerializer):
    ALLOWED = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".doc", ".docx"}

    doc_type_display = serializers.CharField(source="get_doc_type_display", read_only=True)
    uploaded_by_name = serializers.SerializerMethodField()
    size = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ["id", "doc_type", "doc_type_display", "file", "original_name",
                  "application", "is_verified", "uploaded_by_name", "uploaded_at", "size"]
        read_only_fields = ["original_name", "uploaded_at"]
        extra_kwargs = {"file": {"write_only": True}}

    def get_uploaded_by_name(self, obj):
        return obj.uploaded_by.get_full_name() if obj.uploaded_by else "Removed user"

    def get_size(self, obj):
        try:
            return obj.file.size
        except Exception:  # noqa: BLE001 — missing file on a wiped disk
            return None

    def validate_file(self, f):
        ext = os.path.splitext(f.name)[1].lower()
        if ext not in self.ALLOWED:
            raise serializers.ValidationError("Upload a PDF, photo (JPG/PNG) or Word file.")
        if f.size > settings.MAX_DOCUMENT_MB * 1024 * 1024:
            raise serializers.ValidationError(
                f"That file is larger than {settings.MAX_DOCUMENT_MB} MB."
            )
        return f


class StatusChangeSerializer(serializers.ModelSerializer):
    changed_by_name = serializers.SerializerMethodField()
    from_display = serializers.SerializerMethodField()
    to_display = serializers.SerializerMethodField()

    class Meta:
        model = StatusChange
        fields = ["id", "from_status", "from_display", "to_status", "to_display",
                  "changed_by_name", "created_at"]

    def get_changed_by_name(self, obj):
        return obj.changed_by.get_full_name() if obj.changed_by else "Automatic"

    def get_from_display(self, obj):
        return dict(Lead.Status.choices).get(obj.from_status, "")

    def get_to_display(self, obj):
        return dict(Lead.Status.choices).get(obj.to_status, obj.to_status)


class UniversityOptionSerializer(serializers.ModelSerializer):
    """For the 'add application' form in the staff area."""

    country_name = serializers.CharField(source="country.name", read_only=True)
    courses = serializers.SerializerMethodField()

    class Meta:
        model = University
        fields = ["id", "name", "country_name", "courses"]

    def get_courses(self, obj):
        return [{"id": c.id, "name": c.name} for c in obj.courses.all() if c.is_active]


class LeadListSerializer(serializers.ModelSerializer):
    """The counsellor's call list. Deliberately thin — no visa history, no
    documents. Those load only when a lead is actually opened."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    assigned_to_name = serializers.SerializerMethodField()
    countries = serializers.SerializerMethodField()
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Lead
        fields = ["id", "full_name", "phone", "status", "status_display", "source",
                  "assigned_to", "assigned_to_name", "countries", "next_follow_up",
                  "last_contacted_at", "is_overdue", "created_at"]

    def get_assigned_to_name(self, obj):
        return obj.assigned_to.get_full_name() if obj.assigned_to else None

    def get_countries(self, obj):
        return [c.name for c in obj.interested_countries.all()]


class LeadDetailSerializer(LeadListSerializer):
    notes = NoteSerializer(many=True, read_only=True)
    applications = ApplicationSerializer(many=True, read_only=True)
    documents = DocumentSerializer(many=True, read_only=True)
    history = StatusChangeSerializer(source="status_changes", many=True, read_only=True)
    consent_method_display = serializers.CharField(
        source="get_consent_method_display", read_only=True
    )
    created_by_name = serializers.SerializerMethodField()
    visa_history_display = serializers.CharField(
        source="get_visa_history_display", read_only=True
    )

    # Only active staff can receive a student. Assigning to a closed account
    # would make the student invisible to everyone but the owner.
    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True), allow_null=True, required=False,
    )

    class Meta(LeadListSerializer.Meta):
        fields = LeadListSerializer.Meta.fields + [
            "email", "highest_qualification", "completion_year", "study_gap_years",
            "test_type", "test_score", "test_date", "budget_note", "target_intake",
            "visa_history", "visa_history_display", "visa_history_country",
            "visa_history_date", "message", "lost_reason", "notes", "applications",
            "documents", "history", "consent_given", "consent_at", "consent_method_display",
            "created_by_name", "source_detail",
        ]
        # last_contacted_at is stamped by logging a call. Letting it be typed in
        # would let anyone quietly take a student off the "needs a call" list.
        read_only_fields = ["last_contacted_at", "created_at", "consent_given", "consent_at"]

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None

    def validate_phone(self, value):
        return clean_phone(value)


class StaffLeadCreateSerializer(serializers.ModelSerializer):
    """A student added by staff: a walk-in, a phone call, a referral.

    Consent still has to be recorded — it's the same personal data whichever
    door it came through — so staff confirm the student agreed.
    """

    SOURCES = ["walk-in", "phone-call", "referral", "facebook", "whatsapp",
               "instagram", "event", "other"]

    source = serializers.ChoiceField(choices=SOURCES)
    consent_given = serializers.BooleanField()
    consent_method = serializers.ChoiceField(
        choices=[Lead.ConsentMethod.VERBAL, Lead.ConsentMethod.WRITTEN],
        default=Lead.ConsentMethod.VERBAL,
    )
    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True), allow_null=True, required=False,
    )

    class Meta:
        model = Lead
        fields = ["full_name", "phone", "email", "interested_countries", "source",
                  "source_detail", "consent_given", "consent_method", "assigned_to",
                  "highest_qualification", "completion_year", "study_gap_years",
                  "test_type", "test_score", "budget_note", "target_intake",
                  "visa_history", "visa_history_country", "message", "next_follow_up"]

    def validate_phone(self, value):
        return clean_phone(value)

    def validate_consent_given(self, value):
        if not value:
            raise serializers.ValidationError(
                "Confirm the student agreed to be contacted before saving their details."
            )
        return value
