# Interview Questions & Answers — Online Quiz Platform Project

Same 46 questions as before, now with answers. Read these once, then try explaining each
one out loud from memory without looking — that's the real test for an interview.

---

## 1. Django & DRF Fundamentals

**1. Django vs DRF, why both?**
Django is a full-stack web framework — ORM, migrations, admin panel, routing, templates. DRF is a toolkit built on top of Django specifically for building REST APIs: serializers, JSON parsing/rendering, pluggable authentication/permission classes, a browsable API. You need Django's ORM and models regardless; DRF saves you from manually parsing JSON bodies and hand-writing content negotiation for every view.

**2. What does `APIView` add over a plain Django view?**
`request` becomes a DRF `Request` object (`request.data` parses JSON/form/multipart uniformly, unlike Django's raw `request.POST`), the return value is a DRF `Response` that content-negotiates to JSON automatically, and it plugs into `authentication_classes`/`permission_classes` and DRF's exception handling (validation errors become clean JSON 400s instead of raw tracebacks).

**3. `AllowAny` vs `IsAuthenticated`?**
`AllowAny` means no token is required — used on `RegisterView` and the login endpoint since you don't have a token yet at that point. `IsAuthenticated` requires a valid JWT in the `Authorization` header; DRF's `JWTAuthentication` validates it and populates `request.user`, used on every view after login since actions are scoped to a specific user (profile, quiz start, save answer, etc.).

**4. Why serializers instead of returning a model instance directly?**
A model instance is a live Python/DB object — it has methods, related-object references, and non-JSON-native types (`datetime`, `Decimal`). A serializer converts it into plain JSON-compatible data on the way out, and — just as importantly — validates and cleans incoming data (required fields, type coercion, custom rules like `validate_roll_no`) before anything touches the database on the way in.

**5. `Serializer` vs `ModelSerializer`, which did you use?**
Plain `Serializer` requires declaring every field by hand and writing your own `create()`/`update()`. `ModelSerializer` auto-generates fields from `Meta.model` + `Meta.fields`. You used `ModelSerializer` everywhere (`RegisterSerializer`, `UserSerializer`, `QuestionPublicSerializer`, `SessionQuestionSerializer`) since the fields map closely onto models — only overriding `create()` where custom logic was needed (e.g. setting `username = email`).

**6. What does `select_related("question")` do in `_grade_session`?**
It performs a SQL `JOIN` so each `SessionQuestion`'s related `Question` comes back in the *same* query, instead of firing a fresh query per row when you access `sq.question.correct_option` inside the loop — avoiding an N+1 query problem (10 extra queries for a 10-question test, otherwise).

**7. `ForeignKey` vs `OneToOneField` — where did you use each?**
`ForeignKey` is many-to-one: `QuizSession.user` — many sessions *could* reference one user at the model level (your app logic caps it at one, but the DB doesn't). `OneToOneField` is strictly one-to-one: `Profile.user` — each `User` has exactly one `Profile`, enforced at the schema level, never more.

**8. What does `on_delete=CASCADE` do?**
Deleting the referenced row deletes dependent rows too. Since `SessionQuestion.session` has `on_delete=CASCADE`, deleting a `QuizSession` would automatically delete all its `SessionQuestion` rows rather than leaving them orphaned or raising an integrity error.

**9. What does `unique_together = ("session", "question")` prevent?**
It stops the same question from ever appearing twice inside one session — guards against a bug (e.g. an accidental double-insert during `bulk_create`) silently duplicating a question, which would also throw off `attempted_count`/`total_questions` math.

**10. Why did `makemigrations` sometimes need explicit app names?**
You hit this directly — a real Django quirk where a bare `makemigrations` (no app names) can report "No changes detected" and silently skip generating the *initial* migration for an app that has zero prior migrations. Passing the app labels explicitly (`makemigrations accounts quiz`) forces correct detection. Once `0001_initial` exists for an app, plain `makemigrations` works fine for future changes to it.

---

## 2. Authentication & JWT

**11. What is a JWT, three parts?**
A JSON Web Token: **header** (algorithm + token type), **payload** (claims — e.g. user id, expiry timestamp), **signature** (a hash of header+payload signed with a secret key, so tampering is detectable). All three are base64url-encoded and joined with dots: `header.payload.signature`.

**12. Access token vs refresh token, why two lifetimes (30 min / 1 day)?**
The access token is short-lived and sent on every API call to prove identity. The refresh token is longer-lived and used only to obtain a new access token without re-entering the password. Short access lifetime limits the damage window if a token is stolen; the longer refresh lifetime avoids forcing a full re-login every 30 minutes.

**13. Where are JWTs stored on the frontend, and the risk?**
In `localStorage` (see `saveTokens()` in `auth.js`). The risk is XSS: any script that manages to execute on the page (a compromised dependency, injected content) can read `localStorage` and exfiltrate both tokens. The more XSS-resistant alternative is httpOnly cookies (JavaScript can't read them) — but that trades in a new problem: cookies are auto-attached by the browser, so you then need CSRF protection and `SameSite` cookie configuration, adding backend complexity.

**14. Walk through login → dashboard.**
User submits email + password → `loginUser()` POSTs `{username: email, password}` to `/api/login/` → `TokenObtainPairView` calls Django's `authenticate()`, which succeeds because `username` was set to the email at registration → returns `access` + `refresh` → `saveTokens()` writes both to `localStorage` → redirect to `dashboard.html` → `requireAuth()` confirms a token is present → `fetchProfile()` calls `GET /api/profile/` with `Authorization: Bearer <access>` → `JWTAuthentication` validates the token and sets `request.user` → `ProfileView` returns `full_name`/`email`/`roll_no`, rendered on the page.

**15. Why is `username` set to the email at registration?**
Django's built-in `User` model requires a unique `username`. Rather than building a fully custom user model from scratch (subclassing `AbstractBaseUser`, writing a custom manager, setting `USERNAME_FIELD = "email"`, swapping `AUTH_USER_MODEL` — which is disruptive mid-project and essentially requires a fresh database), `RegisterSerializer.create()` just sets `username=email` transparently. The candidate never sees or picks a separate username.

**16. If someone steals a valid access token, what can they do?**
Act as that user for up to 30 minutes on any endpoint requiring `IsAuthenticated` — view profile, hit quiz status/start/submit, etc. They can't get a *new* token after it expires without either the refresh token or the actual password, and the token never exposes the password itself.

**17. `requireAuth()` only checks token *existence* — what's the real security boundary?**
Right — it just checks `localStorage` has *something* in `access_token`, not that it's valid or unexpired. That's a UX convenience (skip straight to the login redirect instead of flashing protected content first). The actual enforcement is server-side: `JWTAuthentication` + `IsAuthenticated` validate the token's signature and expiry on every real API call, returning 401 if it's bad — that's the boundary an attacker can't get around, regardless of what the frontend does or doesn't check.

---

## 3. Database Design

**18. Why `SessionQuestion` instead of a plain `ManyToManyField`?**
A bare `ManyToManyField` only stores *which* questions belong to *which* session — no room for extra per-pair data. You need to store `order`, `selected_option`, and `bookmarked` *per (session, question) pair*, which Django supports via an explicit "through" model — exactly what `SessionQuestion` is.

**19. How does the `order` field let two users see different sequences?**
At session creation, `StartQuizView` shuffles the question bank with `random.sample()`, then `enumerate()`s the result to assign `order = 1..N` on each new `SessionQuestion` row. That order is stored, not recomputed — so `QuizSessionDetailView` always returns questions sorted by the *stored* `order`, meaning the sequence is stable across page reloads for one session, but independently randomized between sessions.

**20. Why is `selected_option` nullable but `correct_option` isn't?**
`correct_option` is fixed metadata, known and required the moment a question is authored. `selected_option` represents "what has the candidate chosen so far" — genuinely unknown/blank until they act, and can return to blank if they hit Clear. Nullability directly models "not yet answered," distinct from any real option value like `"A"`.

**21. What does DB-level `unique=True` on `roll_no` guarantee that the serializer check doesn't?**
It guarantees, at the database engine level, that no two `Profile` rows can ever share a `roll_no` — even under a race condition where two signups with the same roll number land at nearly the same instant. `validate_roll_no()` in the serializer is a friendlier pre-check for the normal flow, but "check then insert" is not atomic (TOCTOU — time-of-check to time-of-use) — the DB constraint is the actual, unconditional guarantee; the serializer check is just a nicer error message in the common case.

**22. What actually happens during `makemigrations` vs `migrate`?**
`makemigrations` reads your current `models.py`, diffs it against the last known migration state (reconstructed from existing migration files), and writes a new migration file describing the change as a sequence of operations (`CreateModel`, `AddField`, etc.) — no database is touched. `migrate` applies those operations against the real database (issuing `CREATE TABLE`/`ALTER TABLE` etc.) and records which migrations have run in the `django_migrations` table.

**23. What did the `showmigrations` bug teach you about migration state vs. real schema?**
`showmigrations quiz` showed `[X] 0001_initial` (Django's bookkeeping said it was applied), but the `bookmarked` column genuinely didn't exist in Postgres. That's a mismatch between Django's *record* of what ran and the database's *actual* schema. It taught that `django_migrations` is just a log — Django doesn't re-verify it against the live schema on every command — so if a migration is interrupted, or the wrong migration history gets carried into a different/fresh database, the two can silently drift apart. The fix was to roll the migration back (`migrate quiz zero`) and reapply it cleanly.

---

## 4. This Project's Core Logic

**24. Walk through `StartQuizView.post()`.**
1. Look up the user's most recent `QuizSession` (if any).
2. If one exists: call `_expire_if_needed()` (auto-grades it if 20 minutes have quietly passed). Then — if it's now `submitted`, return 400 "already attempted"; otherwise return 200 and the *same* `session_id` (resume).
3. If none exists: pull all `Question`s, error out if the bank is empty, `random.sample()` up to 10 of them, create a new `QuizSession`, `bulk_create` the `SessionQuestion` rows with `order = 1..N`, and return 201 with the new `session_id`.

Three outcomes: **refuse** (already attempted), **resume** (in progress), or **create** (first time) — never a fourth path.

**25. How is "only one attempt" actually guaranteed, not just hidden in the UI?**
It's enforced entirely server-side in `StartQuizView` — the check for an existing session happens on every call, regardless of what the frontend does. Even bypassing the UI and calling `/api/quiz/start/` directly via curl/Postman with a valid token hits the exact same logic. (It isn't airtight against a *true* simultaneous double-request race — see Q33 — but holds for the realistic single-tab/single-click flow.)

**26. Why does `_expire_if_needed()` get called from three different places?**
Because a session can go stale passively — a user can sit on the dashboard, or leave the test tab open and idle, without ever calling submit. Every entry point that *reads* a session's state (checking status, fetching the question list, trying to start again) needs to first ask "has time actually run out," so the app never displays a supposedly in-progress test that's secretly expired, and a candidate can't dodge grading simply by never clicking Submit.

**27. Walk through: user starts the test, closes the laptop, comes back 2 hours later.**
They log back in; the dashboard calls `fetchQuizStatus()` → `GET /api/quiz/status/` → finds their `QuizSession` → `_expire_if_needed()` sees elapsed time (2 hrs) ≥ `duration_seconds` (20 min) → calls `_grade_session()` right there, marking it `submitted` with whatever answers were saved before the laptop closed, and scoring every never-answered question as 0/unattempted. The dashboard then shows "already attempted" with that (likely low) score — permanently, since there's only one attempt.

**28. Why compute `remaining_seconds` server-side instead of trusting a frontend countdown?**
Browser-side timers are trivially manipulable — pausing the tab, editing the JS in devtools, changing the system clock. If the countdown itself were authoritative, a user could simply prevent it from ever reaching zero. Because `remaining_seconds` is recalculated from `session.started_at` (a DB timestamp) on every fetch, and `_expire_if_needed()` force-grades once time is *actually* up, there is no client-side way to buy extra time.

**29. What stops a user from submitting someone else's session by guessing the `session_id`?**
`_get_owned_session(user, session_id)` runs `QuizSession.objects.get(id=session_id, user=user)` — if that `session_id` belongs to a different user, the filter matches nothing and the view returns 404, no matter what ID is guessed or brute-forced in the URL. `request.user` itself is never something the client can spoof — it's resolved server-side from the validated JWT.

**30. Why does `not sq.selected_option` correctly catch both "never answered" and "answered then cleared"?**
`selected_option` is normalized server-side in `SaveAnswerView` — `selected_option = request.data.get("selected_option") or None` — so it's always either `None` or a real option string like `"A"`, never an empty string. Both "never touched" and "touched then cleared" end up stored as `None`, and there's no need to distinguish them since they're scored identically anyway (0 marks, counted as unattempted).

**31. Why is bookmark a boolean field on `SessionQuestion` rather than a separate table?**
Bookmark is a property of one specific `(session, question)` pair — exactly the same granularity `selected_option` already lives at. A separate table would need its own `(session, question)` foreign keys plus its own uniqueness constraint, duplicating what `SessionQuestion` already provides, for no real benefit — it's a single flag, not an independently-queried or many-valued concept.

---

## 5. Concurrency & Scalability

**32. What in the design actually makes concurrent users work?**
Every request carries its own JWT identifying its own user, and every view scopes all reads/writes to `request.user` (via `_get_owned_session` or `filter(user=request.user)`) — there's no shared mutable global state and nothing keyed by IP or a shared session dict. Django/WSGI handles one request per worker, and Postgres handles concurrent connections independently — so N users can be mid-test at once without interfering, *provided* the app server actually runs multiple workers (see Q36) and the DB can handle N concurrent connections.

**33. Could two simultaneous `/start/` calls from the same user race each other?**
Yes, in principle. If two requests from the *same* user land at nearly the same instant, both could read `existing = None` before either has committed its new `QuizSession`, and both proceed to create one — leaving that user with two sessions, undermining the single-attempt guarantee. This happens because the check-then-create isn't wrapped in an atomic transaction with a row lock; Postgres's default read-committed isolation doesn't prevent it on its own. In practice this needs a genuinely simultaneous double-click or two open tabs firing together — rare, but real. Fix: wrap the check + create in `transaction.atomic()` with `select_for_update()` on a per-user lock (or an application-level lock), so the second request blocks until the first commits and then correctly sees the just-created session.

**34. Could two sessions get the identical question order?**
Technically possible but astronomically unlikely — with a 10-question bank and `random.sample()` picking all 10, there are 10! (about 3.6 million) possible orderings. Even a coincidental exact match isn't a real problem: it doesn't help anyone cheat, since each candidate still has to actually know the answers. It would only matter if "orders must never repeat" were an actual requirement, which it isn't here.

**35. With 500 students starting at once, what breaks first?**
`manage.py runserver` — Django's single-threaded development server processes one request at a time and is explicitly documented as dev-only; it would fall over (or queue requests badly) long before the database becomes the bottleneck. After switching to a real multi-worker server (see Q36), the next likely bottleneck is Postgres's connection limit (`max_connections`, often ~100 by default) if each worker opens connections without pooling in front.

**36. What changes for a real production deployment?**
Run the app under `gunicorn config.wsgi -w 4` (or similar) instead of `manage.py runserver`, so multiple worker processes actually handle requests in parallel. Put a reverse proxy (nginx) in front for TLS termination and serving static files. Set `DEBUG = False` and a real `ALLOWED_HOSTS` list. At higher concurrency, add a connection pooler like `pgbouncer` in front of Postgres so worker processes aren't each holding their own uncapped connection pool.

**37. Is there a race if `submit` were somehow called twice in parallel for the same session?**
Yes, theoretically — `SubmitQuizView` reads `if session.submitted: return 400` *before* calling `_grade_session()`; two near-simultaneous calls could both read `submitted=False` before either writes `submitted=True`, so `_grade_session()` could run twice. Since it's a deterministic recomputation from the same saved answers, the practical damage is minor (wasted work, not corrupted data) unless an answer write lands in between the two grading runs. To close the gap properly: wrap the fetch-check-grade sequence in `transaction.atomic()` combined with `QuizSession.objects.select_for_update().get(...)`, so the second request blocks on the row lock until the first commits, and then correctly sees `submitted=True` and exits early.

---

## 6. Frontend / API Design

**38. Why does only `test.html` load the Bootstrap JS bundle?**
Only `test.html` uses an *interactive* Bootstrap component — the offcanvas question panel. Bootstrap's interactive widgets (offcanvas, modal, dropdown, etc.) rely on JS (bundled with Popper.js in `bootstrap.bundle.min.js`) to handle `data-bs-toggle`/`data-bs-dismiss` open/close behavior — the CSS alone only provides static styling. Every other page (login, signup, dashboard, etc.) only uses static classes (cards, buttons, form controls), which need nothing beyond the CSS.

**39. Difference between Save and Submit/Finish, in terms of API calls?**
**Save** → `POST /api/quiz/session/<id>/answer/` — persists only the current question's `selected_option`; the session stays in progress and the candidate keeps navigating freely. **Submit/Finish** → `POST /api/quiz/session/<id>/submit/` — grades *every* question in the session at once, sets `submitted = True` permanently, and from that point the `answer/` and `bookmark/` endpoints start rejecting further writes with 400.

**40. Why is the "<5:00 turns red" threshold client-side, but the 20-minute cutoff is server-side?**
The red color is a pure visual/UX cue — nothing about scoring or eligibility depends on it, so it doesn't matter if the client's clock is slightly off. The actual pass/fail time boundary (whether further answers still count) is enforced against `started_at + duration_seconds` on the server specifically *because* that can't be tampered with from devtools, unlike anything computed purely in the browser.

**41. What is CORS, and why is `django-cors-headers` needed here?**
Cross-Origin Resource Sharing — browsers block JavaScript from calling a different origin (protocol + domain + port) than the page was served from, unless the server explicitly allows it. Even though frontend and backend live in one repo, in dev they're served from two different origins (e.g. a static file server on `:5500` vs Django on `:8000` — different port = different origin). Without `django-cors-headers` explicitly permitting it, every `fetch()` call from the frontend to the API would be blocked by the browser with a CORS error.

**42. Why is `CORS_ALLOW_ALL_ORIGINS = True` a problem in production, and what replaces it?**
It lets *any* website on the internet make requests to your API from a visitor's browser, using whatever credentials that browser happens to have cached — defeating the point of CORS as a boundary. Replace it with `CORS_ALLOWED_ORIGINS = ["https://your-real-frontend-domain.com"]`, an explicit allowlist of only the origin(s) that should be permitted to call the API.

---

## 7. Security & Production Readiness

**43. Why does the `.env` change matter, and what's still wrong with `DEBUG=True` / `ALLOWED_HOSTS=["*"]`?**
`.env` (loaded via `python-dotenv`) keeps real secrets — the DB password and Django's `SECRET_KEY` — out of source code and version control, which matters because `SECRET_KEY` signs security-critical data; if it leaks (e.g. committed to a public repo), an attacker can forge trusted tokens. Separately, `DEBUG = True` in production is still dangerous: Django's debug error pages expose full stack tracebacks, local variable values, installed apps, and file paths to *any* visitor who triggers an unhandled exception — a serious information leak. `ALLOWED_HOSTS = ["*"]` disables Django's Host-header validation entirely, opening the door to Host header injection attacks (cache poisoning, poisoned password-reset links, etc.).

**44. Why doesn't a JWT API need CSRF protection the way session-cookie auth does?**
CSRF (Cross-Site Request Forgery) exploits the fact that browsers *automatically* attach cookies to requests — even ones triggered by a completely different, malicious site the user happens to have open. A cookie-authenticated app therefore needs a CSRF token to prove a request genuinely originated from its own frontend. This API doesn't use cookies for auth at all — the JWT is manually attached by JavaScript as an `Authorization` header, and there's no browser mechanism that auto-attaches custom headers cross-site the way it does cookies — so a malicious third-party page cannot silently ride a logged-in user's credentials the way it could with cookie auth.

**45. What would "forgot password" require?**
A way to verify the requester actually owns the email (Django's `PasswordResetTokenGenerator` can generate a time-limited, single-use token), an endpoint to *request* a reset (looks up the user by email, emails a reset link containing the token), an endpoint to *perform* the reset (validates the token, then calls `user.set_password()` and saves), and actual email-sending configuration (an SMTP backend, or a transactional email service like SendGrid) — none of which currently exists in `settings.py`.

**46. Why does hiding `correct_option` at the serializer level (not just the view) matter?**
`QuestionPublicSerializer`'s `fields = [...]` is an explicit *allowlist* — `correct_option` is structurally excluded from anything that serializer produces, no matter what future code does with the queryset. That's safer than relying on view-level discipline ("remember to strip that field before sending"), which is easy to forget under time pressure and easy to silently reintroduce during a refactor — the serializer makes leaking the answer a deliberate, visible code change rather than an easy oversight.

---

**How to use this for prep:** cover the answer column and try to reproduce each one in your own words out loud. Sections 4, 5, and 7 are where interviewers dig deepest on a self-built project — you should be able to defend the concurrency/race-condition answers (24–37, 43–46) without hesitation, since those are the ones that separate "I copied working code" from "I understand what I built."
