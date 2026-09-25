"""
Owner-only management from the staff area, so the client never needs the
Django admin: staff accounts and the public website's content.

Every endpoint here uses IsAdmin, checked on the server. A counsellor who
calls these directly gets 403.
"""

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Country, Course, Lead, Scholarship, TestPrepBatch, University, User
from .permissions import IsAdmin

CLOSED = [Lead.Status.ENROLLED, Lead.Status.LOST]


def _check_password(raw, user):
    try:
        validate_password(raw, user)
    except DjangoValidationError as e:
        raise serializers.ValidationError({"password": list(e.messages)})


# ---------------------------------------------------------------------------
# Staff
# ---------------------------------------------------------------------------

class StaffSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    countries = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(), many=True, required=False
    )
    open_students = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "phone", "role",
                  "bio", "languages", "is_public", "auto_assign", "countries", "is_active",
                  "must_change_password", "last_login", "date_joined", "open_students",
                  "password"]
        read_only_fields = ["is_active", "must_change_password", "last_login", "date_joined"]

    def validate_username(self, value):
        value = value.strip()
        taken = User.objects.filter(username__iexact=value)
        if self.instance:
            taken = taken.exclude(pk=self.instance.pk)
        if taken.exists():
            raise serializers.ValidationError("Someone already uses that username.")
        return value

    def validate(self, attrs):
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": "Give them a temporary password."})
        return attrs

    def create(self, data):
        password = data.pop("password")
        countries = data.pop("countries", [])
        user = User(**data, must_change_password=True)
        _check_password(password, user)
        user.set_password(password)
        user.save()
        user.countries.set(countries)
        return user

    def update(self, user, data):
        data.pop("password", None)  # passwords only change through reset_password
        request = self.context["request"]
        if user == request.user and data.get("role") and data["role"] != User.Role.ADMIN:
            raise serializers.ValidationError(
                {"role": "You can't remove your own owner access. Ask another owner."}
            )
        return super().update(user, data)


class StaffViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                   mixins.CreateModelMixin, mixins.UpdateModelMixin,
                   viewsets.GenericViewSet):
    """Staff accounts. Never deleted — closing an account keeps the person's
    name on every note and call they logged."""

    permission_classes = [IsAdmin]
    serializer_class = StaffSerializer
    pagination_class = None

    def get_queryset(self):
        return (
            User.objects.prefetch_related("countries")
            .annotate(open_students=Count("leads", filter=~Q(leads__status__in=CLOSED)))
            .order_by("-is_active", "role", "first_name", "username")
        )

    @action(detail=True, methods=["post"], url_path="reset-password")
    def reset_password(self, request, pk=None):
        """For a forgotten password: the owner sets a temporary one, the person
        must replace it at next sign-in, and all their devices are signed out."""
        user = self.get_object()
        if user == request.user:
            return Response({"detail": "Change your own password on My account."},
                            status=status.HTTP_400_BAD_REQUEST)
        raw = request.data.get("password") or ""
        _check_password(raw, user)
        user.set_password(raw)
        user.must_change_password = True
        user.save(update_fields=["password", "must_change_password", "password_changed_at"])
        return Response({"detail": f"Temporary password set for {user.username}."})

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        user = self.get_object()
        if user == request.user:
            return Response({"detail": "You can't close your own account."},
                            status=status.HTTP_400_BAD_REQUEST)
        open_count = Lead.objects.filter(assigned_to=user).exclude(status__in=CLOSED).count()
        if open_count:
            # Closing now would strand these students where nobody can see them.
            return Response({"detail": f"{user.get_full_name() or user.username} still has "
                                       f"{open_count} open students. Use Hand over on the Team "
                                       f"page — it moves them and closes the account."},
                            status=status.HTTP_400_BAD_REQUEST)
        if user.is_admin and not User.objects.filter(role=User.Role.ADMIN, is_active=True) \
                .exclude(pk=user.pk).exists():
            return Response({"detail": "This is the last owner account."},
                            status=status.HTTP_400_BAD_REQUEST)
        user.is_active = False
        user.is_public = False
        user.save(update_fields=["is_active", "is_public"])
        return Response(self.get_serializer(self.get_queryset().get(pk=user.pk)).data)

    @action(detail=True, methods=["post"])
    def reactivate(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save(update_fields=["is_active"])
        return Response(self.get_serializer(self.get_queryset().get(pk=user.pk)).data)


# ---------------------------------------------------------------------------
# Website content
# ---------------------------------------------------------------------------

class CountryAdminSerializer(serializers.ModelSerializer):
    slug = serializers.SlugField(required=False, allow_blank=True)
    university_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Country
        fields = ["id", "name", "slug", "summary", "visa_notes", "hero_image_url",
                  "is_active", "sort_order", "university_count"]

    def validate(self, attrs):
        name = attrs.get("name") or getattr(self.instance, "name", "")
        slug = attrs.get("slug") or getattr(self.instance, "slug", "") or slugify(name)
        clash = Country.objects.filter(slug=slug)
        if self.instance:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError({"slug": "Another destination uses that web address."})
        attrs["slug"] = slug
        return attrs


class CourseAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ["id", "university", "name", "level", "duration_months", "tuition_fee",
                  "currency", "intake_months", "is_active"]


class UniversityAdminSerializer(serializers.ModelSerializer):
    courses = CourseAdminSerializer(many=True, read_only=True)
    country_name = serializers.CharField(source="country.name", read_only=True)

    class Meta:
        model = University
        fields = ["id", "country", "country_name", "name", "city", "website", "description",
                  "logo_url", "is_partner", "is_active", "last_verified_on", "courses"]


class ScholarshipAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scholarship
        fields = ["id", "country", "university", "name", "amount_note", "eligibility",
                  "deadline", "link", "is_active"]


class BatchAdminSerializer(serializers.ModelSerializer):
    seats_left = serializers.IntegerField(read_only=True)

    class Meta:
        model = TestPrepBatch
        fields = ["id", "test_type", "title", "start_date", "schedule_note", "duration_weeks",
                  "fee", "total_seats", "seats_taken", "seats_left", "instructor", "is_active"]


class OwnerViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdmin]
    pagination_class = None


class CountryAdminViewSet(OwnerViewSet):
    """Hidden, not deleted, once students or universities point at it."""

    serializer_class = CountryAdminSerializer

    def get_queryset(self):
        return Country.objects.annotate(university_count=Count("universities"))

    def destroy(self, request, *args, **kwargs):
        country = self.get_object()
        if country.universities.exists() or country.leads.exists():
            return Response({"detail": "Students or universities are linked to this "
                                       "destination. Untick Active to hide it instead."},
                            status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)


class UniversityAdminViewSet(OwnerViewSet):
    serializer_class = UniversityAdminSerializer

    def get_queryset(self):
        qs = University.objects.select_related("country").prefetch_related("courses") \
            .order_by("country__sort_order", "name")
        if self.request.query_params.get("country"):
            qs = qs.filter(country_id=self.request.query_params["country"])
        return qs

    def destroy(self, request, *args, **kwargs):
        uni = self.get_object()
        if uni.application_set.exists():
            return Response({"detail": "Students have applications to this university. "
                                       "Untick Active to hide it instead."},
                            status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"], url_path="mark-checked")
    def mark_checked(self, request, pk=None):
        """'I checked these fees today' — shown to students on the website."""
        uni = self.get_object()
        uni.last_verified_on = timezone.localdate()
        uni.save(update_fields=["last_verified_on"])
        return Response(self.get_serializer(uni).data)


class CourseAdminViewSet(OwnerViewSet):
    serializer_class = CourseAdminSerializer
    queryset = Course.objects.all()


class ScholarshipAdminViewSet(OwnerViewSet):
    serializer_class = ScholarshipAdminSerializer

    def get_queryset(self):
        return Scholarship.objects.select_related("country").order_by("country__sort_order",
                                                                      "deadline")


class BatchAdminViewSet(OwnerViewSet):
    serializer_class = BatchAdminSerializer
    queryset = TestPrepBatch.objects.order_by("-start_date")
