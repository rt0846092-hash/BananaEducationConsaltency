"""
Creates the owner account on first deploy, from environment variables:

    OWNER_USERNAME   e.g. owner
    OWNER_EMAIL      where new-student alerts go
    OWNER_PASSWORD   typed into the Render dashboard by the owner, nobody else

Runs on every deploy (see build.sh) but only ever *creates*: if the account
already exists nothing is touched, so a password changed in the app is never
overwritten. Delete OWNER_PASSWORD from Render once you've signed in.
"""

import os

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

from core.models import User


class Command(BaseCommand):
    help = "Create the owner account from OWNER_* environment variables, once."

    def handle(self, *args, **options):
        username = os.getenv("OWNER_USERNAME", "").strip()
        password = os.getenv("OWNER_PASSWORD", "")
        email = os.getenv("OWNER_EMAIL", "").strip()

        if not username:
            self.stdout.write("ensure_owner: OWNER_USERNAME not set — skipping.")
            return
        if User.objects.filter(username=username).exists():
            self.stdout.write(f"ensure_owner: '{username}' already exists — leaving it alone.")
            return
        if not password:
            self.stdout.write(self.style.WARNING(
                f"ensure_owner: set OWNER_PASSWORD in the Render dashboard to create "
                f"'{username}', then redeploy."
            ))
            return
        try:
            validate_password(password, User(username=username, email=email))
        except ValidationError as e:
            # Don't fail the whole deploy over this; say exactly what to fix.
            self.stdout.write(self.style.ERROR(
                "ensure_owner: OWNER_PASSWORD was not accepted: " + " ".join(e.messages)
                + " Choose a longer one and redeploy."
            ))
            return

        User.objects.create_superuser(
            username=username, email=email, password=password,
            first_name=os.getenv("OWNER_FIRST_NAME", ""), last_name=os.getenv("OWNER_LAST_NAME", ""),
            is_public=False,
        )
        self.stdout.write(self.style.SUCCESS(
            f"ensure_owner: created owner '{username}'. Remove OWNER_PASSWORD from Render now."
        ))
