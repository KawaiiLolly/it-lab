# Django + JWT Auth + Online Quiz System (PostgreSQL + Bootstrap frontend)

## Folder structure
```
auth_project/
├── backend/
│   ├── config/          # Django project settings, urls
│   ├── accounts/        # register/login/profile (+ roll_no)
│   ├── quiz/            # question bank, sessions, scoring, single-attempt logic
│   ├── manage.py
│   └── requirements.txt
└── frontend/
    ├── login.html
    ├── signup.html
    ├── dashboard.html      # name, roll no, email, attempt status
    ├── instructions.html   # pre-test rules, marking scheme, "1 attempt only" notice
    ├── test.html            # the live, timed test — collapsible question panel, bookmarks
    ├── result.html          # post-submit summary + Exit App
    ├── css/
    └── js/
```

## Backend setup

1. Create a PostgreSQL database:
   ```sql
   CREATE DATABASE auth_db;
   ```
   Update credentials in `backend/config/settings.py` under `DATABASES` if yours differ.

2. Install dependencies:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate     # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Run migrations and seed the question bank (10 sample questions):
   ```bash
   python manage.py makemigrations accounts quiz
   python manage.py migrate
   python manage.py seed_questions
   python manage.py runserver
   ```
   > Note: name the apps explicitly (`accounts quiz`) the first time. A bare
   > `makemigrations` with no app names can report "No changes detected" and skip
   > creating the initial migrations for apps that don't have any yet — a known
   > Django quirk, not an error in your setup. Once `0001_initial.py` exists for
   > both apps, a plain `makemigrations` works fine for any future model changes.
   >
   > If you already ran migrations from an earlier version of this project (before
   > bookmarking was added), just run `python manage.py makemigrations quiz` again
   > to pick up the new `bookmarked` field, then `python manage.py migrate`.
   >
   > Same idea if you're upgrading from a version that had a separate username field:
   > run `python manage.py makemigrations accounts` to pick up the new `full_name`
   > column on `Profile`, then `python manage.py migrate`. Any accounts created
   > before this change won't have a `full_name` set — easiest is to re-register
   > test accounts, or set it manually via `/admin/`.

   API is now live at `http://127.0.0.1:8000/api/`. You can add/edit questions later
   at `http://127.0.0.1:8000/admin/` (create a superuser first with `createsuperuser`).

## API endpoints

| Method | Endpoint                          | Body / Notes                                       | Auth required |
|--------|-------------------------------------|-------------------------------------------------------|---------------|
| POST   | `/api/register/`                   | `full_name, email, password, roll_no`                 | No |
| POST   | `/api/login/`                      | `username, password` — send the candidate's **email** as `username` (see note below) | No — returns `access` + `refresh` JWT |
| POST   | `/api/token/refresh/`              | `refresh`                                               | No |
| GET    | `/api/profile/`                    | —                                                        | Yes |
| GET    | `/api/quiz/status/`                | Has this user attempted / got a session in progress?    | Yes |
| POST   | `/api/quiz/start/`                 | Starts a new attempt, or **resumes** an in-progress one; refused if already submitted | Yes |
| GET    | `/api/quiz/session/<id>/`          | Questions (this session's order) + time left            | Yes |
| POST   | `/api/quiz/session/<id>/answer/`   | `question_id, selected_option` (null = clear)            | Yes |
| POST   | `/api/quiz/session/<id>/bookmark/` | `question_id, bookmarked` (true/false)                   | Yes |
| POST   | `/api/quiz/session/<id>/submit/`   | Grades and locks the session                             | Yes |

## How it works

- **No username, anywhere**: candidates sign up with Full Name, Email, Roll No, and Password —
  there's no username field in the UI at all. Internally, Django's `User` model still needs a
  `username` column, so `RegisterSerializer` quietly sets it to the candidate's email address.
  The login page collects email + password and the frontend sends that email as the `username`
  value the `/api/login/` endpoint (Simple JWT) expects — the candidate never sees this detail.
  Full name and roll number live on a separate `Profile` model.
- **Question bank**: a single shared `Question` table (10 seeded rows). Each *session*
  (one per test attempt) gets its own randomly shuffled order via `QuizSession` +
  `SessionQuestion` — so concurrent users never see the same sequence, and each JWT-authenticated
  request only ever touches that user's own session (enforced in every view).
- **Single attempt**: `POST /api/quiz/start/` checks for an existing session for that user.
  - None yet → creates one.
  - One exists and is still within the 20-minute window → **resumes** it (same session id,
    answers/bookmarks already saved are intact) — so a refresh or lost connection doesn't cost
    the candidate their attempt.
  - One exists and is either submitted, or its 20 minutes have quietly expired → the request
    is refused with "You have already attempted this test."
  Expired-but-unsubmitted sessions are auto-graded the moment they're touched again (via
  `status/`, the session detail fetch, or a new `start/` call), so a candidate can't dodge
  grading by simply closing the tab.
- **Timing**: `started_at` is stored server-side when the session is created. `remaining_seconds`
  is calculated from the server clock on every fetch, so the 20-minute limit can't be tampered
  with from the browser. The frontend timer counts down locally, turns red under 5:00, and
  auto-submits at zero.
- **Bookmarks**: each question in a session can be flagged independently of its answer, via the
  bookmark button on the test page — shown as a star both on the button and in the question grid.
- **Save / Clear**: each question's selection is saved individually via the `answer/` endpoint —
  so answers persist even if the candidate navigates away and back before submitting.
- **Scoring**: on submit, each question is graded once: `+5` correct, `-2` incorrect, `0` unattempted.
  The session is marked `submitted` and can't be resubmitted or edited afterward.
- **Concurrency**: because every request is authenticated by its own JWT and reads/writes only
  its own `QuizSession` rows, multiple users can take the test at the same time with no shared
  state. For real concurrent load in production, run the backend with multiple workers
  (e.g. `gunicorn config.wsgi -w 4`).

## Frontend setup

No build tools needed — plain HTML/CSS/JS + Bootstrap 5 (CSS via CDN; `test.html` also loads the
Bootstrap JS bundle, needed for the collapsible question panel).

1. Serve the `frontend/` folder with any static server, e.g. `python -m http.server 5500`
   (or just open the HTML files directly in a browser).
2. `js/auth.js` points `API_BASE` to `http://127.0.0.1:8000/api` — change it if your backend
   runs elsewhere.

## Flow

`signup.html` → `login.html` → `dashboard.html` (details + attempt status) →
`instructions.html` (rules, marking scheme, one-attempt notice) → `test.html`
(timed, one question at a time, collapsible 4-per-row question panel, Save/Clear/Bookmark,
Prev/Next, Submit) → `result.html` (attempted count + marks + **Exit App**, which logs out
and returns to `login.html`).

If a candidate has already attempted the test, `dashboard.html` and `instructions.html` show
their result summary instead of a Start button — no retakes.

This is a minimal, single-question-bank starting point — for production you'd want HTTPS,
environment-based secrets, stricter CORS settings, and question-bank management tooling.
