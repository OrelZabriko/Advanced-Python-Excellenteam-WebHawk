# WebHawk Users Service — Edge Cases & Hardening Notes

Status snapshot: `/register`, `/login`, `/logout`, `/validate` are implemented and
verified end-to-end against a real Postgres instance (register → login → validate
→ logout → validate-rejected). This document lists what's **not yet handled**,
organized by priority, to guide the next round of work.

---

## 1. Input validation gaps

| Area | Current behavior | Risk | Suggested fix |
|---|---|---|---|
| Email format | Any non-empty string accepted (`"asdf"` passes) | Garbage data in `users.email`; no real validation of deliverability | Add a regex or `email-validator` package check in `register_user` |
| Password strength | Any non-empty string accepted (`"a"` passes) | Weak passwords, no minimum length/complexity | Enforce min length (e.g. 8+ chars) before hashing |
| Email case sensitivity | `Alice@Example.com` and `alice@example.com` are treated as different users (Postgres `UNIQUE` is case-sensitive by default) | Duplicate accounts for the same real email; login confusion | Normalize email to lowercase before every DB read/write (`email.strip().lower()`) |
| Whitespace | `"  alice@example.com  "` stored as-is with leading/trailing spaces | Duplicate-looking accounts; login failures if user retypes without spaces | `.strip()` email (and arguably password, though trailing spaces in passwords are sometimes intentional — decide per policy) |
| Request body type | `request.get_json(silent=True) or {}` silently treats non-JSON bodies as empty dict | Non-JSON requests fail with generic "email and password required" instead of a clearer "expected JSON body" message | Optionally check `request.is_json` and return a distinct 400 for malformed content-type |

---

## 2. Authentication & session edge cases

| Area | Current behavior | Risk | Suggested fix |
|---|---|---|---|
| Rate limiting on `/login` | None | Brute-force password guessing is unthrottled | Add rate limiting (e.g. `Flask-Limiter`) per-IP and/or per-email on `/login` and `/register` |
| Rate limiting on `/register` | None | Automated mass account creation / email enumeration at scale | Same as above |
| Account lockout | None — unlimited login attempts against one account | Credential stuffing / brute force against a known email | Consider lockout or exponential backoff after N failed attempts |
| Token refresh | Not implemented — token is valid for a fixed `JWT_EXPIRY_SECS` (24h by default), then the user must log in again | Poor UX for long sessions; no way to extend a session without re-entering credentials | Add a `/refresh` endpoint that issues a new token if the current one is still within a grace period, without requiring password re-entry |
| Multiple concurrent sessions | Supported implicitly (each login creates a new `jti`/session row) — but there's no way for a user to view or revoke *other* active sessions (e.g. "log out all devices") | If a token is stolen, the legitimate user has no way to force-revoke it remotely (short of changing their password, which isn't implemented either) | Add a `GET /sessions` (list active sessions for a user) and `POST /sessions/revoke-all` endpoint |
| Expired-token cleanup | `user_sessions` rows are never deleted, even after `expires_at` passes — they just stop matching the `expires_at > NOW()` check in `get_active_session` | Table grows unbounded over time | Add a periodic cleanup job (cron / scheduled task) to delete or archive sessions older than some retention window |
| Password reset | Not implemented at all | Users who forget their password have no recovery path | Requires email delivery infrastructure — likely out of scope for this service alone, but worth flagging as a gap |
| Password change | Not implemented — no endpoint to change password while logged in | Compromised password can't be rotated by the user | Add a `PATCH /users/me/password` endpoint (requires current password + new password) |

---

## 3. Error handling & information disclosure

| Area | Current behavior | Risk | Suggested fix |
|---|---|---|---|
| Login error messages | Same message ("invalid email or password") for both "email not found" and "wrong password" — **this is intentional and correct**, prevents email enumeration | None — this is already hardened correctly | No action needed; documented here to confirm it's deliberate, not an oversight |
| Register error messages | "a user with this email already exists" (409) — **reveals whether an email is registered** | Email enumeration: an attacker can probe `/register` with a list of emails to discover which ones have accounts | Consider returning a generic "if this email can be registered, you'll receive next steps" response regardless of whether the email exists (requires rethinking the register flow, e.g. email verification) — flagging as a known tradeoff, not necessarily wrong for this project's scope |
| Internal errors | Any unhandled exception (e.g. DB connection failure) currently returns Flask's default 500 HTML error page, not JSON | Inconsistent API responses; leaks stack traces if `debug=True` reaches production | Add a global Flask error handler (`@app.errorhandler(Exception)`) to return consistent JSON `{"error": "internal server error"}` with a 500, and ensure `debug=False` in any non-local environment |
| Database connection failures | `get_connection()` will raise an unhandled `psycopg2.OperationalError` if Postgres is down | Same as above — leaks internals, inconsistent error shape | Wrap repository calls or add a global handler as above |

---

## 4. Data integrity & concurrency

| Area | Current behavior | Risk | Suggested fix |
|---|---|---|---|
| Register race condition | `get_user_by_email` check happens, then `create_user` insert happens as two separate steps (not atomic) | Two near-simultaneous `/register` calls with the same email could both pass the existence check before either inserts, causing a race | Rely on the DB's `UNIQUE` constraint on `email` as the real guard — catch the resulting `IntegrityError`/`UniqueViolation` in `create_user` and translate it to the same 409 `ServiceError`, rather than trusting the pre-check alone |
| Connection handling under load | Every repository call opens and closes a brand-new `psycopg2` connection | Under real traffic, constant connect/disconnect overhead; risk of exhausting Postgres's `max_connections` under concurrent load | Introduce a connection pool (e.g. `psycopg2.pool.SimpleConnectionPool` or SQLAlchemy) once traffic patterns justify it — noted in `connection.py`'s own comment as a deliberate simplification for now |
| IP address spoofing | `request.remote_addr` is trusted as-is and stored in `user_sessions.ip` | If the service sits behind a reverse proxy/load balancer, `remote_addr` may reflect the proxy's IP, not the real client — or be spoofable via `X-Forwarded-For` if not configured correctly | If deployed behind a proxy, configure Flask's `ProxyFix` middleware and validate which forwarded-for header (if any) is trustworthy in your infrastructure |

---

## 5. Configuration & secrets

| Area | Current behavior | Risk | Suggested fix |
|---|---|---|---|
| `.env` in repo | `.gitignore` correctly excludes `.env` — confirmed not committed | None currently, but flag for awareness | Keep it this way; ensure any deployment pipeline injects real secrets via environment variables, not a committed file |
| JWT secret rotation | No mechanism to rotate `JWT_SECRET` without invalidating every existing session at once | If the secret is ever compromised, rotating it logs out all users simultaneously with no graceful transition | Consider a key-ID (`kid`) claim + supporting multiple valid secrets during a rotation window, if this becomes a real requirement |
| Default/fallback secrets | **Fixed** — `Config.JWT_SECRET` and `Config.DB_PASSWORD` no longer have a fallback value at all; the service now refuses to start with a clear `RuntimeError` if either is unset, instead of silently running on a known, guessable value | None currently | No action needed; kept here as a record of what changed and why |

---

## 6. Testing gaps

| Area | Current state |
|---|---|
| Automated tests | None yet — verification so far has been manual `curl` testing against a live Postgres instance |
| Suggested next step | Add a `pytest` suite covering: successful register/login/validate/logout flow, duplicate email rejection, wrong password rejection, expired token rejection, revoked session rejection, malformed JSON body handling |
| Test database | No separate test DB/schema — tests would currently run against the same dev Postgres instance | Consider a dedicated test database (or transactional rollback per test) to avoid polluting dev data |

---

## Priority summary (suggested order to tackle)

1. **High** — Global error handler for unhandled exceptions (prevents leaking stack traces / inconsistent error shapes)
2. **High** — Email normalization (lowercase + strip) to prevent duplicate-looking accounts
3. **High** — Rate limiting on `/login` and `/register`
4. **Medium** — Handle the register race condition via DB constraint + exception translation
5. **Medium** — Basic password strength validation
6. **Medium** — Automated test suite (pytest)
7. **Low** — Token refresh endpoint
8. **Low** — Session listing / "log out all devices"
9. **Low** — Connection pooling (only if/when real load justifies it)
10. **Low** — JWT secret rotation strategy (only relevant if this goes to production with real users)