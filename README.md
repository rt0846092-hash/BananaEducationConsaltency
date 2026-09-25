# Banana Education Consultancy

A study-abroad consultancy site with a public lead-capture flow and a staff back office.
Django REST API + React (Vite, Tailwind). Deploys to Render and Vercel.

Everything in the seed data is invented. Fees, universities and students are samples for
the demo.

---

## What it does

The public side has one job: turn a visitor into a phone number the office can call.
The private side has one job: make sure that number never gets forgotten.

A student scans a QR code, answers three questions, and their details are in the database
before they see the second screen. A counsellor sees only their own students. The owner
sees everything, plus the one number that matters — how many leads nobody has called in
48 hours.

### Who can do what

| | Viewer | Student | Counsellor | Owner |
|---|---|---|---|---|
| Browse countries, universities, fees, classes | ✓ | ✓ | ✓ | ✓ |
| Fill in the counselling form | | ✓ | | |
| See and work on their own students | | | ✓ | ✓ (everyone) |
| Add a walk-in / phone / referral student | | | ✓ (to themselves) | ✓ (to anyone) |
| Log calls, change stage, set follow-ups, WhatsApp | | | ✓ | ✓ |
| Add university applications and move them through stages | | | ✓ | ✓ |
| Upload, download and verify documents | | | ✓ | ✓ |
| Record expected commission | | | | ✓ |
| Assign and reassign students, hand over a whole caseload | | | | ✓ |
| Team workload, reports with date ranges, CSV export (logged) | | | | ✓ |

### What happens when a student fills in the form

1. Their details are saved immediately (before anything else can fail).
2. A repeat submission from the same number — in any format — is merged into the
   existing record instead of creating a second student.
3. They're assigned automatically: to an active counsellor who handles one of their
   chosen countries, whoever has the fewest open students. Set which countries each
   counsellor handles in the Django admin → Users. `AUTO_ASSIGN=False` turns this off.
4. The counsellor and owner get an email; the student gets a confirmation if they gave
   an email address. Emails never block or undo the save.

---

## Run it locally

You need Python 3.11+, Node 18+, and either MySQL or nothing at all (it falls back to
SQLite so you can start without installing a database).

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # then edit it
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

API at `http://localhost:8000/api/`, Django admin at `http://localhost:8000/admin/`.

Seeded logins, all with password `banana123`:

| Username  | Role       | Sees                          |
|-----------|------------|-------------------------------|
| `admin`   | Owner      | Every lead, every report      |
| `sarita`  | Counsellor | Only students assigned to her |
| `mingma`  | Counsellor | Only students assigned to him |

For MySQL, create the database with the right charset first. MySQL's `utf8` is a 3-byte
charset that silently mangles Korean, Nepali and Bengali names:

```sql
CREATE DATABASE banana CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Then set `DATABASE_URL=mysql://root:yourpassword@127.0.0.1:3306/banana` in `.env`.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Site at `http://localhost:5173`.

---

## Deploy

**Quickest:** Render dashboard → New → Blueprint → choose this repo. `render.yaml` creates
the database, the API and the website together; you only fill in the two addresses.
The manual steps below do the same thing by hand (and show the Vercel option).

On Render's free plan the API goes to sleep when nobody uses it, so the first visitor
after a quiet spell waits while it wakes. For a real client, use a paid instance so the
form always answers quickly.

### Database

Render does not offer managed MySQL, only PostgreSQL. Because the code reads a single
`DATABASE_URL`, both work without changing a line.

- **Easiest:** create a free Postgres instance on Render and copy its Internal Database URL.
- **If you need MySQL:** use Aiven, Railway or PlanetScale and paste that connection string
  instead.

### Backend on Render

New → Web Service → connect your repo.

| Setting | Value |
|---|---|
| Root directory | `backend` |
| Build command | `./build.sh` |
| Start command | `gunicorn config.wsgi:application` |

Environment variables:

```
SECRET_KEY          a long random string
DEBUG               False
DATABASE_URL        from the step above
CORS_ALLOWED_ORIGINS  https://your-app.vercel.app
ALLOWED_HOSTS       your-api.onrender.com
```

After the first deploy, open the Render shell and run `python manage.py seed_demo`.

### Frontend on Vercel

New Project → import the same repo.

| Setting | Value |
|---|---|
| Root directory | `frontend` |
| Framework | Vite |

One environment variable:

```
VITE_API_URL   https://your-api.onrender.com/api
```

`vercel.json` already handles SPA routing, so `/apply` won't 404 on a hard refresh.

### The order that saves you an evening

Deploy the backend first and confirm `https://your-api.onrender.com/api/countries/`
returns JSON in the browser. Only then deploy the frontend. If you do it the other way
round you'll be debugging a blank page with no idea which half is broken.

---

## The QR codes

Point each printed code at `/apply` with its own source tag:

```
https://your-app.vercel.app/apply?src=office-door
https://your-app.vercel.app/apply?src=fair-jan
https://your-app.vercel.app/apply?src=brochure
```

Same form every time. The tag is saved with the lead, so the owner can see that the
education fair produced eleven students and the brochures produced none. That one field
is most of the reason a client keeps paying you monthly.

---

## The one rule you must not break

Permissions live in `get_queryset`, not in the interface.

```python
# core/views.py — StaffLeadAccess
def get_queryset(self):
    qs = Lead.objects.all()
    if self.request.user.is_admin:
        return qs
    return qs.filter(assigned_to=self.request.user)
```

Hiding a button in React hides nothing. Anyone can open the browser console and call
`/api/leads/` directly. Filtering the queryset means the rows never leave the database.

This matters more here than in most projects. The `Lead` table holds phone numbers,
family budgets and visa refusal history belonging to real people, often teenagers. A leak
isn't embarrassing, it's harmful — and the client's competitor would happily pay for that
list.

**Test it before you take anyone's money.** Log in as `sarita`, then open
`/api/leads/` directly in the URL bar. You should see 4 students, not 12.

Or let the tests check it for you, as every role:

```bash
cd backend && python manage.py test core      # 58 API tests: viewer, student, staff, admin
```

`e2e/personas.py` drives a real browser through the same four roles (see the
comment at the top of the file for how to run it).

---

## Brand assets

Everything the site needs sits in `frontend/public/` and Vite copies it to the build
untouched.

| File | Used for |
|---|---|
| `favicon.svg` | Browser tab. Scales to any size, stays sharp |
| `favicon.ico` | Fallback for older browsers and the bookmarks bar |
| `apple-touch-icon.png` | iPhone home screen when a student saves the site |
| `icon-192.png`, `icon-512.png` | Android home screen, listed in the manifest |
| `og-image.png` | The preview card when the link is shared |

The mark is a single arc with a rounded cap. Nothing thinner survives at 16 pixels — a
tapered crescent looked better at full size and disappeared in the browser tab.

`og-image.png` is the one people forget. Consultancies market on Facebook and WhatsApp, so
the shared link *is* the advert. Without an `og:image` the preview is a grey box with a URL
in it, and nobody taps a grey box. To change the wording, edit the SVG source and
re-export at exactly 1200×630.

The header logo is inline SVG in `src/components/Logo.jsx` rather than an image file, so it
inherits colour from whatever it sits on. Pass `tile={false}` for the crescent alone.

---

## Settings that matter in production

Backend (see `backend/.env.example` for all of them):

| Variable | Why |
|---|---|
| `AWS_STORAGE_BUCKET_NAME`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (+ `AWS_S3_ENDPOINT_URL` for Cloudflare R2) | **Required before real documents are uploaded.** Render wipes its disk on every deploy. The staff area shows a warning until this is set. |
| `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | New-student alerts. Without them emails are only printed to the log. |
| `FRONTEND_URL`, `OFFICE_NAME`, `OFFICE_PHONE` | Used in email text and links. |
| `AUTO_ASSIGN` | `False` leaves new website students for the owner to assign. |

Frontend: `VITE_API_URL`, `VITE_OFFICE_NAME`, `VITE_OFFICE_PHONE`, `VITE_OFFICE_PHONE_TEL`,
`VITE_OFFICE_EMAIL`. Leave `VITE_DEMO_MODE` unset for a real client — the demo logins are
then left out of the build completely, not just hidden.

`seed_demo` with `DEBUG=False` gives every account a random password, printed once, which
must be changed at first sign-in.

## Still to build

1. A student portal (students checking progress and uploading their own documents).
   Needs sign-in by SMS code, which needs an SMS provider account.
2. WhatsApp or SMS alerts to counsellors. The WhatsApp button on each student already
   opens a chat; automatic messages need the WhatsApp Business API.
3. Several branches, each with its own students and staff.
4. Commission in more than one currency. Reports assume US dollars.

---

## Before this goes live for a real client

- Change every seeded password.
- Replace the sample universities and fees with content the client supplies, and keep the
  `last_verified_on` date honest.
- Delete the invented scholarship entries.
- Never add invented visa success rates or testimonials. They attract regulators and they
  are the first thing a competitor screenshots.
- Fill in the privacy page template (`src/pages/Privacy.jsx`), have it checked, and remove
  its yellow notice. It is already linked from the consent checkbox and the footer.

- Agree in writing how many content edits per month the retainer covers, or you will be
  adding universities for free at midnight.
