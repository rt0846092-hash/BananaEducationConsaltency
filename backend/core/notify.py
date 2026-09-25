"""
Emails. Every function here is called *after* the database write and never
raises: a mail outage must not lose an enquiry or break a staff action.

With no EMAIL_HOST set, Django prints messages to the server log instead of
sending them, which is what you want on a laptop.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail

from .models import User

log = logging.getLogger(__name__)


def _send(subject, body, recipients):
    recipients = sorted({r for r in recipients if r})
    if not recipients:
        return
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=False)
    except Exception:  # noqa: BLE001 — never let mail break the request
        log.exception("Could not send email '%s' to %s", subject, recipients)


def _link(lead):
    return f"{settings.FRONTEND_URL.rstrip('/')}/staff/leads/{lead.pk}"


def _owners():
    return list(
        User.objects.filter(is_active=True, role=User.Role.ADMIN)
        .exclude(email="").values_list("email", flat=True)
    ) + list(getattr(settings, "OFFICE_NOTIFY_EMAILS", []))


def new_student(lead):
    """To the counsellor who got the student, and the owner."""
    countries = ", ".join(c.name for c in lead.interested_countries.all()) or "not chosen"
    who = lead.assigned_to.get_full_name() if lead.assigned_to else "nobody yet — please assign"
    body = (
        f"{lead.full_name} asked for counselling.\n\n"
        f"Phone:     {lead.phone}\n"
        f"Countries: {countries}\n"
        f"Source:    {lead.source or 'unknown'}\n"
        f"Assigned:  {who}\n\n"
        f"Call within the hour if you can — interest cools fast.\n{_link(lead)}\n"
    )
    to = _owners()
    if lead.assigned_to and lead.assigned_to.email:
        to.append(lead.assigned_to.email)
    _send(f"New student: {lead.full_name}", body, to)


def assigned_to_you(lead, person, by):
    if not person or not person.email or person == by:
        return
    _send(
        f"Student assigned to you: {lead.full_name}",
        f"{by.get_full_name() or by.username} assigned {lead.full_name} "
        f"({lead.phone}) to you.\n\n{_link(lead)}\n",
        [person.email],
    )


def handover_received(person, count, by):
    if not person.email or count == 0:
        return
    _send(
        f"{count} students handed over to you",
        f"{by.get_full_name() or by.username} moved {count} students to you. "
        f"Each is marked for a call today.\n\n{settings.FRONTEND_URL.rstrip('/')}/staff\n",
        [person.email],
    )


def student_confirmation(lead):
    """Only if they gave an email. The phone call is still the real follow-up."""
    if not lead.email:
        return
    _send(
        f"{settings.OFFICE_NAME}: we have your details",
        f"Hello {lead.full_name.split()[0]},\n\n"
        f"Thank you for contacting {settings.OFFICE_NAME}. A counsellor will call you on "
        f"{lead.phone} within one working day.\n\n"
        f"If you'd rather not wait, call us on {settings.OFFICE_PHONE}.\n",
        [lead.email],
    )
