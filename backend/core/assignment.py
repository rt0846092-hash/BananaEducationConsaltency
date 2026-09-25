"""
Who gets a new student from the website.

Without this, every form submission sat unassigned until the owner noticed it,
and no counsellor could see it in the meantime. The rule is deliberately
simple so the owner can predict it:

1. Only active counsellors with "auto assign" switched on take part.
2. If some of them handle one of the student's chosen countries, only they
   are considered.
3. Of those, the person with the fewest open students gets this one.
   Ties go to whoever joined first.

Turn it off for the whole office with AUTO_ASSIGN=False.
"""

from django.conf import settings
from django.db.models import Count, Q

from .models import Assignment, Lead, User

CLOSED = [Lead.Status.ENROLLED, Lead.Status.LOST]


def pick_counsellor(lead):
    if not getattr(settings, "AUTO_ASSIGN", True):
        return None

    pool = User.objects.filter(
        is_active=True, role=User.Role.COUNSELLOR, auto_assign=True
    )
    wanted = list(lead.interested_countries.values_list("id", flat=True))
    if wanted:
        specialists = pool.filter(countries__in=wanted).distinct()
        if specialists.exists():
            pool = specialists

    return (
        pool.annotate(open_count=Count("leads", filter=~Q(leads__status__in=CLOSED)))
        .order_by("open_count", "date_joined", "id")
        .first()
    )


def auto_assign(lead):
    person = pick_counsellor(lead)
    if person is None:
        return None
    lead.assigned_to = person
    lead.save(update_fields=["assigned_to", "updated_at"])
    Assignment.objects.create(
        lead=lead, from_user=None, to_user=person, changed_by=None,
        reason="Automatic — new student from the website",
    )
    return person
