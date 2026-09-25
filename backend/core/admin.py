from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from .models import (
    Application, Assignment, Country, Course, Document, ExportLog, Lead, Note,
    Scholarship, StatusChange, TestPrepBatch, University, User,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["username", "get_full_name", "role", "must_change_password",
                    "is_public", "is_active"]
    list_filter = ["role", "is_public", "is_active"]
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Consultancy profile", {
            "fields": ("role", "must_change_password", "phone", "photo_url", "bio",
                       "languages", "is_public")
        }),
        ("New students from the website", {
            "fields": ("auto_assign", "countries"),
            "description": "New students go to an active counsellor with automatic "
                           "assignment on, preferring those who handle the student's "
                           "chosen country, then whoever has the fewest open students.",
        }),
    )
    filter_horizontal = BaseUserAdmin.filter_horizontal + ("countries",)
    # Without these the owner could create an account but not choose its role,
    # and after resetting a password could not force the person to replace it.
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Consultancy profile", {
            "fields": ("first_name", "last_name", "role", "must_change_password")
        }),
    )


class CourseInline(admin.TabularInline):
    model = Course
    extra = 1


@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ["name", "country", "city", "is_partner", "last_verified_on", "is_active"]
    list_filter = ["country", "is_partner", "is_active"]
    search_fields = ["name", "city"]
    inlines = [CourseInline]


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ["name", "sort_order", "is_active"]
    list_editable = ["sort_order", "is_active"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Scholarship)
class ScholarshipAdmin(admin.ModelAdmin):
    list_display = ["name", "country", "amount_note", "deadline", "is_active"]
    list_filter = ["country", "is_active"]


@admin.register(TestPrepBatch)
class TestPrepBatchAdmin(admin.ModelAdmin):
    list_display = ["__str__", "start_date", "seats_left", "fee", "is_active"]
    list_filter = ["test_type", "is_active"]


class NoteInline(admin.TabularInline):
    """Notes are the call record. New ones can be added here; old ones are
    never edited or deleted, so what was said on a call can't be rewritten."""

    model = Note
    extra = 0
    fields = ["body", "is_call_log", "author", "created_at"]
    readonly_fields = ["author", "created_at"]
    can_delete = False

    def has_change_permission(self, request, obj=None):
        return False


class ApplicationInline(admin.TabularInline):
    model = Application
    extra = 0


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ["full_name", "phone", "status", "assigned_to", "source",
                    "next_follow_up", "overdue_flag", "created_at"]
    list_filter = ["status", "assigned_to", "source", "visa_history", "interested_countries"]
    search_fields = ["full_name", "phone", "email"]
    filter_horizontal = ["interested_countries"]
    readonly_fields = ["created_at", "updated_at", "consent_at", "consent_method",
                       "created_by", "phone_key"]
    inlines = [ApplicationInline, NoteInline]

    def save_formset(self, request, form, formset, change):
        for obj in formset.save(commit=False):
            if isinstance(obj, Note) and not obj.author_id:
                obj.author = request.user
            obj.save()
        formset.save_m2m()
    date_hierarchy = "created_at"

    @admin.display(description="Overdue")
    def overdue_flag(self, obj):
        if obj.is_overdue:
            return format_html('<b style="color:#B45309">Needs a call</b>')
        return "—"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.is_admin:
            return qs
        return qs.filter(assigned_to=request.user)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ["lead", "university", "intake", "status", "deadline"]
    list_filter = ["status", "university__country"]


class ReadOnlyLog(admin.ModelAdmin):
    """Audit trails lose their value if they can be edited. Viewable, never
    changed or deleted — not even by the owner."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ExportLog)
class ExportLogAdmin(ReadOnlyLog):
    list_display = ["created_at", "user", "row_count", "filters", "ip_address"]


@admin.register(Assignment)
class AssignmentAdmin(ReadOnlyLog):
    list_display = ["created_at", "lead", "from_user", "to_user", "changed_by", "reason"]


@admin.register(StatusChange)
class StatusChangeAdmin(ReadOnlyLog):
    list_display = ["created_at", "lead", "from_status", "to_status", "changed_by"]


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["lead", "doc_type", "original_name", "is_verified", "uploaded_by",
                    "uploaded_at"]
    list_filter = ["doc_type", "is_verified"]
