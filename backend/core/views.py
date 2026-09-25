import csv
import logging
import mimetypes
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q, Sum
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import generics, status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.decorators import throttle_classes
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from . import notify
from .assignment import auto_assign
from .models import (
    Application, Assignment, Country, Document, ExportLog, Lead, Note, StatusChange,
    TestPrepBatch, University, User, phone_key,
)
from .permissions import IsAdmin
from .serializers import (
    AccountSerializer, ApplicationSerializer, BatchSerializer, CounsellorSerializer, CountryDetailSerializer,
    CountryListSerializer, DocumentSerializer, IntakeStepOneSerializer,
    IntakeStepTwoSerializer, LeadDetailSerializer, LeadListSerializer, NoteSerializer,
    StaffLeadCreateSerializer, UniversityOptionSerializer,
)


class IntakeThrottle(AnonRateThrottle):
    scope = "intake"


class LoginThrottle(AnonRateThrottle):
    scope = "login"


class Login(TokenObtainPairView):
    """Same as the default, with its own tighter limit so guessing passwords
    runs out long before browsing does."""

    throttle_classes = [LoginThrottle]


CLOSED = [Lead.Status.ENROLLED, Lead.Status.LOST]
log = logging.getLogger(__name__)

# Step two is reached with a signed token, not a database ID. IDs are
# sequential, so an ID-based URL let a stranger walk the range and overwrite
# other students' answers during their first hour.
INTAKE_SALT = "banana.intake"
INTAKE_MAX_AGE = 60 * 60


def _intake_token(lead_id, duplicate=False):
    return signing.dumps({"lead": lead_id, "dup": duplicate}, salt=INTAKE_SALT)


def visible_leads(user):
    """The one rule: owners see every student, counsellors only their own.
    Every staff endpoint that touches a student goes through here."""
    qs = Lead.objects.all()
    return qs if user.is_admin else qs.filter(assigned_to=user)


def record_status(lead, old, new, by):
    if old != new:
        StatusChange.objects.create(lead=lead, from_status=old or "", to_status=new,
                                    changed_by=by)


# ---------------------------------------------------------------------------
# Public — no login
# ---------------------------------------------------------------------------

class CountryList(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CountryListSerializer
    pagination_class = None
    queryset = (
        Country.objects.filter(is_active=True)
        .annotate(university_count=Count("universities", filter=Q(universities__is_active=True)))
    )


class CountryDetail(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = CountryDetailSerializer
    lookup_field = "slug"
    queryset = Country.objects.filter(is_active=True)


class BatchList(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = BatchSerializer
    pagination_class = None

    def get_queryset(self):
        return TestPrepBatch.objects.filter(
            is_active=True, start_date__gte=timezone.localdate()
        )[:6]


class CounsellorList(generics.ListAPIView):
    """Who appears on the public site. A new account used to appear the moment
    it was created — nameless, bio-less, before the person had even signed in.
    Now only staff who have finished setting up and written a bio are shown."""

    permission_classes = [AllowAny]
    serializer_class = CounsellorSerializer
    pagination_class = None
    queryset = (User.objects.filter(is_public=True, is_active=True, must_change_password=False)
                .exclude(bio=""))


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([IntakeThrottle])
def lead_intake(request):
    """Step one of the QR form.

    The order here is the whole point: the lead is written to the database
    first and any notification happens afterwards. If it were the other way
    round and the mail service were down, the inquiry would vanish and nobody
    would know it ever existed. A lost lead is lost commission.

    Every outcome returns the same shape — a token and nothing else — so the
    response never reveals whether a phone number is already on file.
    """
    serializer = IntakeStepOneSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    # Honeypot: real people leave this blank, bots fill it. Return a success
    # response anyway so the bot does not learn it was caught.
    if request.data.get("website"):
        return Response({"token": _intake_token(0)}, status=status.HTTP_201_CREATED)

    lead = serializer.save()

    # Same person scanning the poster twice should not become two students.
    duplicate = (
        Lead.objects.filter(phone_key=lead.phone_key,
                            created_at__gte=timezone.now() - timedelta(days=30))
        .exclude(pk=lead.pk).order_by("created_at").first()
    )
    if duplicate:
        Note.objects.create(
            lead=duplicate,
            body=f"Submitted the form again from source '{lead.source or 'unknown'}'.",
        )
        lead.delete()
        return Response({"token": _intake_token(duplicate.pk, duplicate=True)},
                        status=status.HTTP_201_CREATED)

    record_status(lead, "", lead.status, None)
    auto_assign(lead)

    # Notifications come last, and never raise.
    notify.new_student(lead)
    notify.student_confirmation(lead)
    return Response({"token": _intake_token(lead.pk)}, status=status.HTTP_201_CREATED)


@api_view(["PATCH"])
@permission_classes([AllowAny])
@throttle_classes([IntakeThrottle])
def lead_intake_details(request):
    """Step two. Needs the signed token from step one, valid for an hour.

    For a returning student the answers are added as a note rather than
    written over the record a counsellor may already be working from.
    """
    try:
        claim = signing.loads(request.data.get("token") or "", salt=INTAKE_SALT,
                              max_age=INTAKE_MAX_AGE)
        lead = Lead.objects.get(pk=claim["lead"])
    except (signing.BadSignature, KeyError, TypeError, Lead.DoesNotExist):
        return Response({"detail": "This form has expired."}, status=status.HTTP_404_NOT_FOUND)

    serializer = IntakeStepTwoSerializer(lead, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)

    if claim.get("dup") or lead.status != Lead.Status.NEW:
        answers = [f"{k.replace('_', ' ')}: {v}" for k, v in serializer.validated_data.items()
                   if v not in ("", None)]
        if answers:
            Note.objects.create(lead=lead, body="Details from a repeat form submission:\n"
                                + "\n".join(answers))
    else:
        serializer.save()
    return Response({"ok": True})


# ---------------------------------------------------------------------------
# Staff — login required
# ---------------------------------------------------------------------------

# These two stay reachable while the flag is set — otherwise there would be no
# way to clear it. Naming IsAuthenticated explicitly replaces the project
# default, which includes PasswordIsSet.
def _me_payload(user):
    return {
        "id": user.id,
        "name": user.get_full_name() or user.username,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "phone": user.phone,
        "bio": user.bio,
        "languages": user.languages,
        "is_public": user.is_public,
        "role": user.role,
        "is_admin": user.is_admin,
        "must_change_password": user.must_change_password,
        "documents_persistent": settings.DOCUMENTS_PERSISTENT,
    }


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def me(request):
    user = request.user
    if request.method == "PATCH":
        # Choose a real password before anything else can change.
        if user.must_change_password:
            return Response({"detail": "Set your own password before continuing."},
                            status=status.HTTP_403_FORBIDDEN)
        serializer = AccountSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
    return Response(_me_payload(user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password(request):
    user = request.user
    current = request.data.get("current_password") or ""
    new = request.data.get("new_password") or ""

    if not user.check_password(current):
        return Response({"current_password": ["That isn't your current password."]},
                        status=status.HTTP_400_BAD_REQUEST)
    if current == new:
        return Response({"new_password": ["Choose something different from the old one."]},
                        status=status.HTTP_400_BAD_REQUEST)

    try:
        validate_password(new, user)
    except ValidationError as e:
        return Response({"new_password": list(e.messages)},
                        status=status.HTTP_400_BAD_REQUEST)

    user.set_password(new)
    user.must_change_password = False
    user.save(update_fields=["password", "must_change_password", "password_changed_at"])

    # Every other device is now signed out. Hand this one a fresh token so the
    # person who just changed their password isn't thrown out too.
    return Response({"detail": "Password updated.",
                     "access": str(RefreshToken.for_user(user).access_token)})


class StaffLeadAccess:
    """The rule that makes the whole system safe.

    Permissions are applied to the queryset, not to the interface. Hiding a
    button in React hides nothing — anyone can open the browser console and
    call the API directly. Filtering here means the rows never leave the
    database in the first place.
    """

    def get_queryset(self):
        return (
            visible_leads(self.request.user)
            .prefetch_related("interested_countries")
            .select_related("assigned_to")
        )


class LeadList(StaffLeadAccess, generics.ListCreateAPIView):
    def get_serializer_class(self):
        return StaffLeadCreateSerializer if self.request.method == "POST" else LeadListSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        if params.get("status"):
            qs = qs.filter(status=params["status"])
        if params.get("unassigned") == "true":
            qs = qs.filter(assigned_to__isnull=True)
        if params.get("search"):
            term = params["search"]
            digits = phone_key(term)
            match = Q(full_name__icontains=term) | Q(phone__icontains=term)
            if len(digits) >= 4:
                match |= Q(phone_key__contains=digits)
            qs = qs.filter(match)
        if params.get("overdue") == "true":
            stale = timezone.now() - timedelta(hours=48)
            qs = qs.exclude(status__in=CLOSED).filter(
                Q(last_contacted_at__isnull=True, created_at__lt=stale)
                | Q(next_follow_up__lt=timezone.localdate())
            )
        return qs

    def create(self, request, *args, **kwargs):
        """A walk-in, a phone call, a referral — anyone who didn't use the form.

        A counsellor's new student is always theirs. The owner can hand it to
        anyone, or leave it unassigned.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        data = serializer.validated_data

        existing = Lead.objects.filter(phone_key=phone_key(data["phone"])).first()
        if existing:
            if visible_leads(user).filter(pk=existing.pk).exists():
                return Response({"detail": f"{existing.full_name} already has this number.",
                                 "existing_id": existing.pk}, status=status.HTTP_409_CONFLICT)
            # Say it exists — staff need to know — but show nothing about them.
            return Response({"detail": "This number belongs to a student another counsellor "
                                       "is handling. Ask the owner to move them to you."},
                            status=status.HTTP_409_CONFLICT)

        assignee = data.pop("assigned_to", None) if user.is_admin else user
        if not user.is_admin:
            data.pop("assigned_to", None)
        countries = data.pop("interested_countries", [])
        data.pop("consent_given")

        now = timezone.now()
        with transaction.atomic():
            # The person adding them is talking to them right now, so this
            # counts as the first contact and they start as "contacted".
            lead = Lead.objects.create(
                **data, assigned_to=assignee, created_by=user, consent_given=True,
                consent_at=now, status=Lead.Status.CONTACTED, last_contacted_at=now,
            )
            lead.interested_countries.set(countries)
            record_status(lead, "", lead.status, user)
            Note.objects.create(
                lead=lead, author=user, is_call_log=True,
                body=f"Added by {user.get_full_name() or user.username} "
                     f"({lead.source.replace('-', ' ')}). "
                     f"Consent: {lead.get_consent_method_display().lower()}.",
            )
            if assignee:
                Assignment.objects.create(lead=lead, to_user=assignee, changed_by=user,
                                          reason="Added by staff")
        notify.assigned_to_you(lead, assignee, user)
        return Response(LeadDetailSerializer(lead).data, status=status.HTTP_201_CREATED)


class LeadDetail(StaffLeadAccess, generics.RetrieveUpdateAPIView):
    serializer_class = LeadDetailSerializer

    def get_queryset(self):
        return super().get_queryset().prefetch_related(
            "notes__author", "applications__university__country", "applications__course",
            "documents__uploaded_by", "status_changes__changed_by",
        )

    def perform_update(self, serializer):
        # Reassigning a student is an owner decision, not a counsellor one.
        if "assigned_to" in serializer.validated_data and not self.request.user.is_admin:
            serializer.validated_data.pop("assigned_to")

        previous = serializer.instance.assigned_to
        old_status = serializer.instance.status
        lead = serializer.save()
        record_status(lead, old_status, lead.status, self.request.user)

        # Every handover leaves a trace. This protects the owner as much as it
        # constrains them: when a counsellor says "you took my student", the
        # log answers it.
        if lead.assigned_to != previous:
            Assignment.objects.create(
                lead=lead, from_user=previous, to_user=lead.assigned_to,
                changed_by=self.request.user, reason="Reassigned by hand",
            )
            notify.assigned_to_you(lead, lead.assigned_to, self.request.user)


@api_view(["POST"])
def add_note(request, pk):
    lead = get_object_or_404(visible_leads(request.user), pk=pk)

    serializer = NoteSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    note = serializer.save(lead=lead, author=request.user)

    if note.is_call_log:
        lead.last_contacted_at = timezone.now()
        old = lead.status
        if lead.status == Lead.Status.NEW:
            lead.status = Lead.Status.CONTACTED
        lead.save(update_fields=["last_contacted_at", "status", "updated_at"])
        record_status(lead, old, lead.status, request.user)

    return Response(NoteSerializer(note).data, status=status.HTTP_201_CREATED)


# --- Applications to universities ------------------------------------------

@api_view(["GET"])
def university_options(request):
    qs = (University.objects.filter(is_active=True, country__is_active=True)
          .select_related("country").prefetch_related("courses")
          .order_by("country__sort_order", "name"))
    return Response(UniversityOptionSerializer(qs, many=True).data)


def _commission_guard(request, data):
    """Expected commission is the owner's business figure, not a counsellor's."""
    if not request.user.is_admin:
        data.pop("commission_expected", None)


@api_view(["POST"])
def add_application(request, pk):
    lead = get_object_or_404(visible_leads(request.user), pk=pk)
    serializer = ApplicationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    _commission_guard(request, serializer.validated_data)
    app = serializer.save(lead=lead)
    Note.objects.create(lead=lead, author=request.user,
                        body=f"Application added: {app.university.name} "
                             f"({app.get_status_display()}).")
    return Response(ApplicationSerializer(app).data, status=status.HTTP_201_CREATED)


@api_view(["PATCH"])
def update_application(request, pk):
    app = get_object_or_404(
        Application.objects.filter(lead__in=visible_leads(request.user)), pk=pk
    )
    old = app.get_status_display()
    serializer = ApplicationSerializer(app, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    _commission_guard(request, serializer.validated_data)
    app = serializer.save()
    if app.get_status_display() != old:
        Note.objects.create(lead=app.lead, author=request.user,
                            body=f"{app.university.name}: {old} → {app.get_status_display()}.")
    return Response(ApplicationSerializer(app).data)


# --- Documents ---------------------------------------------------------------

@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def upload_document(request, pk):
    lead = get_object_or_404(visible_leads(request.user), pk=pk)
    serializer = DocumentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    app = serializer.validated_data.get("application")
    if app and app.lead_id != lead.pk:
        raise DRFValidationError({"application": "That application belongs to another student."})
    doc = serializer.save(lead=lead, uploaded_by=request.user,
                          original_name=request.data["file"].name[:200])
    return Response(DocumentSerializer(doc).data, status=status.HTTP_201_CREATED)


def _visible_document(request, pk):
    return get_object_or_404(
        Document.objects.filter(lead__in=visible_leads(request.user)), pk=pk
    )


@api_view(["GET"])
def download_document(request, pk):
    doc = _visible_document(request, pk)
    try:
        handle = doc.file.open("rb")
    except (FileNotFoundError, OSError):
        return Response({"detail": "The file is missing from storage. Upload it again."},
                        status=status.HTTP_404_NOT_FOUND)
    name = doc.original_name or doc.file.name.rsplit("/", 1)[-1]
    return FileResponse(handle, as_attachment=True, filename=name,
                        content_type=mimetypes.guess_type(name)[0] or "application/octet-stream")


@api_view(["PATCH", "DELETE"])
def document_detail(request, pk):
    doc = _visible_document(request, pk)
    if request.method == "DELETE":
        # A verified document is part of the file. Only the owner removes it.
        if doc.is_verified and not request.user.is_admin:
            return Response({"detail": "Verified documents can only be removed by the owner."},
                            status=status.HTTP_403_FORBIDDEN)
        doc.file.delete(save=False)
        doc.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    if "is_verified" in request.data:
        doc.is_verified = str(request.data["is_verified"]).lower() in ("true", "1")
        doc.save(update_fields=["is_verified"])
    return Response(DocumentSerializer(doc).data)


@api_view(["GET"])
def dashboard(request):
    """The owner's morning screen.

    `uncontacted` is the number that matters. It is the one thing an owner
    cannot get from a notebook or a WhatsApp group, and it is the reason they
    open this page every day.
    """
    qs = visible_leads(request.user)

    week_ago = timezone.now() - timedelta(days=7)
    stale = timezone.now() - timedelta(hours=48)
    live = qs.exclude(status__in=CLOSED)
    year_start = timezone.localdate().replace(month=1, day=1)

    return Response({
        "new_this_week": qs.filter(created_at__gte=week_ago).count(),
        "uncontacted": live.filter(last_contacted_at__isnull=True, created_at__lt=stale).count(),
        "follow_up_today": live.filter(next_follow_up=timezone.localdate()).count(),
        "unassigned": live.filter(assigned_to__isnull=True).count(),
        # Counted from when the stage was set to enrolled, not from the last
        # time anyone edited the record.
        "enrolled_this_year": _enrolled_since(qs, year_start),
        "by_status": list(qs.values("status").annotate(count=Count("id")).order_by()),
        "by_source": list(
            qs.filter(created_at__gte=week_ago)
            .values("source").annotate(count=Count("id")).order_by("-count")[:8]
        ),
        "by_country": list(
            qs.values("interested_countries__name")
            .annotate(count=Count("id")).order_by("-count")[:8]
        ),
    })


def _enrolled_since(qs, day):
    """Counted from when the stage was set to enrolled, not from the last time
    anyone edited the record (which moved January edits into the new year).
    Students enrolled before stage history existed fall back to updated_at."""
    moves = StatusChange.objects.filter(lead=OuterRef("pk"), to_status=Lead.Status.ENROLLED)
    return (
        qs.filter(status=Lead.Status.ENROLLED)
        .filter(Q(Exists(moves.filter(created_at__date__gte=day)))
                | (~Q(Exists(moves)) & Q(updated_at__date__gte=day)))
        .count()
    )


# ---------------------------------------------------------------------------
# Owner only
# ---------------------------------------------------------------------------

def _overdue_filter(prefix="leads__"):
    """Someone is overdue if nobody has called them within 48 hours of arriving,
    or their follow-up date has passed. Closed cases are never overdue."""
    stale = timezone.now() - timedelta(hours=48)
    return (
        Q(**{f"{prefix}last_contacted_at__isnull": True, f"{prefix}created_at__lt": stale})
        | Q(**{f"{prefix}next_follow_up__lt": timezone.localdate()})
    ) & ~Q(**{f"{prefix}status__in": CLOSED})


@api_view(["GET"])
@permission_classes([IsAdmin])
def team(request):
    """Who works here, how loaded they are, and who is falling behind.

    Useful every day, not only when somebody resigns.
    """
    people = (
        User.objects.filter(is_active=True)
        .annotate(
            total=Count("leads", distinct=True),
            live=Count("leads", distinct=True, filter=~Q(leads__status__in=CLOSED)),
            enrolled=Count("leads", distinct=True, filter=Q(leads__status=Lead.Status.ENROLLED)),
            overdue=Count("leads", distinct=True, filter=_overdue_filter()),
        )
        .prefetch_related("countries")
        .order_by("-total")
    )

    return Response([
        {
            "id": p.id,
            "name": p.get_full_name() or p.username,
            "username": p.username,
            "role": p.role,
            "languages": p.languages,
            "countries": [c.name for c in p.countries.all()],
            "auto_assign": p.auto_assign and p.role == User.Role.COUNSELLOR,
            "total": p.total,
            "live": p.live,
            "enrolled": p.enrolled,
            "overdue": p.overdue,
        }
        for p in people
    ])


@api_view(["POST"])
@permission_classes([IsAdmin])
def handover(request):
    """Move one person's students to somebody else, optionally closing their
    account.

    The whole thing runs inside a transaction. Deactivating an account but
    failing halfway through the reassignment would leave students attached to
    a login nobody can use — invisible to everyone until a parent rings up
    asking why nobody called back.
    """
    from_id = request.data.get("from_user")
    to_id = request.data.get("to_user")
    reason = (request.data.get("reason") or "").strip()
    # bool("false") is True, so a string from a form or script would close
    # the account by accident. Accept only real yes values.
    deactivate = str(request.data.get("deactivate", "")).strip().lower() in ("true", "1", "yes", "on")

    if not from_id or not to_id:
        return Response({"detail": "Choose who is handing over and who receives."},
                        status=status.HTTP_400_BAD_REQUEST)
    if str(from_id) == str(to_id):
        return Response({"detail": "Those are the same person."},
                        status=status.HTTP_400_BAD_REQUEST)

    try:
        leaving = User.objects.get(pk=from_id)
        receiving = User.objects.get(pk=to_id, is_active=True)
    except (User.DoesNotExist, ValueError):
        return Response({"detail": "That staff member no longer exists."},
                        status=status.HTTP_404_NOT_FOUND)

    if leaving == request.user and deactivate:
        return Response({"detail": "You cannot close your own account here."},
                        status=status.HTTP_400_BAD_REQUEST)

    open_leads = list(Lead.objects.filter(assigned_to=leaving).exclude(status__in=CLOSED))

    with transaction.atomic():
        for lead in open_leads:
            Assignment.objects.create(
                lead=lead, from_user=leaving, to_user=receiving,
                changed_by=request.user,
                reason=reason or f"Handover from {leaving.get_full_name() or leaving.username}",
            )
            lead.assigned_to = receiving
            # Flag them for a call rather than letting them arrive silently.
            # Fourteen strangers appearing in your list with no signal is
            # exactly how students get dropped.
            lead.next_follow_up = timezone.localdate()
            lead.save(update_fields=["assigned_to", "next_follow_up", "updated_at"])

            Note.objects.create(
                lead=lead, author=request.user,
                body=f"Handed over to {receiving.get_full_name() or receiving.username}."
                     + (f" {reason}" if reason else ""),
            )

        if deactivate:
            # Deactivate, never delete. A deleted user takes their name off
            # every historical note with them.
            leaving.is_active = False
            leaving.is_public = False
            leaving.save(update_fields=["is_active", "is_public"])

    notify.handover_received(receiving, len(open_leads), request.user)
    return Response({
        "moved": len(open_leads),
        "to": receiving.get_full_name() or receiving.username,
        "deactivated": deactivate,
    })


def _date_range(request):
    """?from=2026-01-01&to=2026-03-31 — either end optional, both inclusive."""
    raw_from, raw_to = request.query_params.get("from"), request.query_params.get("to")
    start = parse_date(raw_from) if raw_from else None
    end = parse_date(raw_to) if raw_to else None
    if (raw_from and not start) or (raw_to and not end):
        raise DRFValidationError({"detail": "Dates must look like 2026-01-31."})
    if start and end and start > end:
        raise DRFValidationError({"detail": "The start date is after the end date."})
    return start, end


def _in_range(qs, start, end, field="created_at"):
    if start:
        qs = qs.filter(**{f"{field}__date__gte": start})
    if end:
        qs = qs.filter(**{f"{field}__date__lte": end})
    return qs


@api_view(["GET"])
@permission_classes([IsAdmin])
def reports(request):
    """Money in flight and how the funnel is actually performing.

    With a date range, everything is about students who *enquired* in that
    period — so a spring fair can be judged by what its students went on to do.
    """
    start, end = _date_range(request)
    leads = _in_range(Lead.objects.all(), start, end)
    apps = Application.objects.filter(lead__in=leads)

    live_stages = [
        Application.Status.SUBMITTED,
        Application.Status.OFFER_CONDITIONAL,
        Application.Status.OFFER_UNCONDITIONAL,
        Application.Status.VISA_FILED,
        Application.Status.VISA_APPROVED,
    ]

    by_stage = (
        apps.values("status")
        .annotate(count=Count("id"), value=Sum("commission_expected"))
        .order_by("-count")
    )
    stage_labels = dict(Application.Status.choices)

    return Response({
        "range": {"from": start, "to": end},
        "pipeline_value": apps.filter(status__in=live_stages)
                          .aggregate(v=Sum("commission_expected"))["v"] or 0,
        "won_value": apps.filter(status=Application.Status.ENROLLED)
                     .aggregate(v=Sum("commission_expected"))["v"] or 0,
        "by_stage": [
            {"status": r["status"], "label": stage_labels.get(r["status"], r["status"]),
             "count": r["count"], "value": r["value"] or 0}
            for r in by_stage
        ],
        "funnel": [
            {"label": "Enquiries", "count": leads.count()},
            {"label": "Applied somewhere",
             "count": leads.filter(applications__isnull=False).distinct().count()},
            {"label": "Received an offer", "count": leads.filter(
                applications__status__in=[Application.Status.OFFER_CONDITIONAL,
                                          Application.Status.OFFER_UNCONDITIONAL],
            ).distinct().count()},
            {"label": "Enrolled", "count": leads.filter(status=Lead.Status.ENROLLED).count()},
        ],
        "by_source": [
            {"source": r["source"] or "unknown", "count": r["count"],
             "enrolled": r["enrolled"]}
            for r in leads.values("source").annotate(
                count=Count("id"), enrolled=Count("id", filter=Q(status=Lead.Status.ENROLLED))
            ).order_by("-count")[:12]
        ],
        "by_country": list(
            leads.values("interested_countries__name")
            .annotate(count=Count("id")).order_by("-count")[:8]
        ),
    })


@api_view(["POST"])
@permission_classes([IsAdmin])
def delete_lead(request, pk):
    """Permanently remove a student and everything about them.

    For a student who asks for their data to be deleted (the privacy page
    promises this), and for clearing sample data before going live. Owner
    only, and the full name must be typed to confirm — there is no undo.
    For anyone who simply stopped replying, set the stage to Lost instead.
    """
    lead = get_object_or_404(Lead, pk=pk)
    if (request.data.get("confirm_name") or "").strip() != lead.full_name.strip():
        return Response({"detail": "Type the student's full name exactly to confirm."},
                        status=status.HTTP_400_BAD_REQUEST)
    name = lead.full_name
    for doc in lead.documents.all():
        doc.file.delete(save=False)
    lead.delete()
    log.info("Student %s (id %s) deleted by %s", name, pk, request.user.username)
    return Response({"detail": f"{name} and all their records were deleted."})


@api_view(["GET"])
@permission_classes([IsAdmin])
def export_leads(request):
    """Admin only, and every export is recorded.

    A counsellor who leaves for a competitor should not be able to walk out
    with the client's contact list. That restriction is the product, not a
    technical detail — say it out loud when you pitch this.

    Accepts the same filters as the reports page: from, to, status, source,
    assigned_to. The filters used are saved in the export log.
    """
    start, end = _date_range(request)
    params = request.query_params
    leads = _in_range(Lead.objects.all(), start, end)
    if params.get("status"):
        leads = leads.filter(status=params["status"])
    if params.get("source"):
        leads = leads.filter(source=params["source"])
    if params.get("assigned_to"):
        leads = leads.filter(assigned_to_id=params["assigned_to"])
    leads = leads.select_related("assigned_to").prefetch_related("interested_countries")

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="students-{timezone.localdate()}.csv"'
    )
    # Excel opens UTF-8 CSVs correctly only with a byte-order mark; without it
    # Nepali and Korean names turn into gibberish.
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow([
        "Name", "Phone", "Email", "Countries", "Status", "Assigned to", "Source",
        "Qualification", "Study gap", "Test", "Score", "Visa history",
        "Next follow-up", "Created",
    ])
    rows = 0
    for lead in leads:
        rows += 1
        writer.writerow([
            lead.full_name, lead.phone, lead.email,
            ", ".join(c.name for c in lead.interested_countries.all()),
            lead.get_status_display(),
            lead.assigned_to.get_full_name() if lead.assigned_to else "",
            lead.source, lead.highest_qualification, lead.study_gap_years,
            lead.test_type, lead.test_score, lead.get_visa_history_display(),
            lead.next_follow_up or "", lead.created_at.date(),
        ])

    used = "&".join(f"{k}={v}" for k, v in params.items()
                    if k in ("from", "to", "status", "source", "assigned_to") and v)
    ExportLog.objects.create(
        user=request.user, row_count=rows, filters=used[:300],
        ip_address=request.META.get("REMOTE_ADDR"),
    )
    return response
