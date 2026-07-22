# WebHawk — Advanced Python Excellenteam Final Project
WebHawk is a security middleware platform: every incoming request is checked for
SQL injection, XSS, and rate-limit abuse before it is forwarded to the real
backend it protects.


---
 
## Team
 
| Name | ID | Email |
|---|---|---|
| Benny Beer | 312556657 | bennybe@edu.jmc.ac.il |
| Nadav Ben Melech | 211728316 | nadavbenm@edu.jmc.ac.il |
| Orel Zabriko | 211845458 | orelzab@edu.jmc.ac.il |
 
---
 
## Services
 
| Compose service | Source folder | Host port | Role |
|---|---|---|---|
| `middleware` | `middleware/` | **8080** | Public entry point. All protected traffic. |
| `security_engine` | `services/security_engine/` | 8081 | SQLi / XSS / rate-limit detection. |
| `users` | `services/users/` | 8082 | Registration, login, JWT issue and revoke. |
| `backend_registry` | `services/backend_registry/` | 8083 | Backend registration and API key issuance. |
| `postgres` | — | 5432 | Shared database. |

**On the port numbers:** each service has two ports that serve different
purposes. The *host* port (in the table above — 8080/8081/8082/8083) is what
you hit from outside Docker — Postman on Windows, or a browser. Every
service's *internal* port — what it actually binds to inside its own
container — is **8080**, regardless of which service it is. `security_engine`
listens on `0.0.0.0:8080` inside its container just like `users`
does, even though its host port is 8081.

This split matters once services start calling each other: traffic between
containers on the same Docker network never goes through the host port
mapping at all — a container reaches another container's own internal port
directly. So when the middleware calls `http://security_engine:...`, that
URL has to end in `:8080`, not `:8081`, even though `:8081` is what you'd
use from Postman on the host. Getting this backwards is a common and
confusing source of "connection refused" errors, since it works fine from
Postman and fails only in container-to-container calls.

Every service hardcodes `port=8080` directly in its own `app.py` - not read
from `.env`, and not centralized in `services/shared/config.py` either, the
same way `services/security_engine/app.py`'s own `app.run(port=8080)` call
already did before this. `services/users/Dockerfile`'s `EXPOSE`/bind reflects
this too: 8080 internally, mapped to 8082 externally in `docker-compose.yml`.

Every port above is published to the host during development, so each service
can be tested directly in Postman. Before the final demo, consider removing
the non-middleware `ports:` entries so the middleware is the only reachable
service.

---

## Prerequisites

- **Python 3.11+** — [python.org/downloads](https://www.python.org/downloads/)
  (check "Add Python to PATH" during install)
- **Docker Desktop for Windows** (with the WSL 2 backend, which Docker Desktop
  installs for you — you don't work inside WSL, Docker just uses it internally)
- **Git for Windows**

Verify:
```powershell
python --version
docker --version
docker compose version
```

---

## Setup

### 1. Clone

```powershell
git clone https://github.com/OrelZabriko/Advanced-Python-Excellenteam-WebHawk.git
cd Advanced-Python-Excellenteam-WebHawk
```

### 2. Create and activate a virtual environment, then install requirements

Do this **before** running anything else — even if you plan to run the whole
system through Docker. Two reasons it matters regardless of Docker:

- VS Code and PyCharm both need a real interpreter with the packages installed
  to resolve imports and give useful autocomplete/error-checking. Without it,
  every `from services.shared...` import shows as unresolved in the editor,
  even though it works fine at runtime.
- The helper scripts in `scripts/` (`test_connection.py`, `test_jwt.py`) run
  directly on your machine, not inside a container — they need the venv active
  to find their dependencies.

```powershell
# Create the venv (once, at the repo root)
python -m venv .venv

# Activate it (every new terminal session)
.\.venv\Scripts\Activate.ps1

# Install every dependency the project needs
pip install -r requirements.txt
```

If PowerShell blocks the activation script with an execution-policy error,
allow it for the current session only:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

You'll know the venv is active because the prompt shows `(.venv)` at the start
of the line. Leave it active for every step below.

> **What's actually in `requirements.txt`?** Flask (the web framework),
> psycopg2-binary (Postgres driver), bcrypt (password hashing), PyJWT (token
> signing), python-dotenv (`.env` loading), requests (the middleware's HTTP
> client to the other services), and gunicorn — see the callout below for
> what that last one is and why it only matters inside Docker.

### 3. Create your `.env`

All secrets and per-environment settings live in a single `.env` at the repo
root, which is **never committed**. Copy the template:

```powershell
Copy-Item .env.example .env
```

Then open `.env` and set at minimum `DB_USER`, `DB_PASSWORD`, and `JWT_SECRET`.

Generate a real JWT secret rather than typing one — humans are bad at being
random, and every token the system signs is only as safe as this value:

```powershell
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
```

**`.env` syntax rule:** each line must be `KEY=VALUE`, with no spaces around
`=` and no trailing comment on a value line. `DB_HOST=postgres # docker` is
parsed as the literal value `postgres # docker` and breaks the connection.

### 4. Run everything

With the venv active and `.env` filled in:

```bash
docker compose up --build
```
 
This builds and starts every service on one Docker network, and initialises
Postgres automatically from the `.sql` files in `db/`.
 
To reset completely - dropping all users, registrations, logs and rate-limit
counters:
 
```bash
docker compose down -v && docker compose up --build
```
 
The `-v` flag is what drops the Postgres volume. Without it, old rows survive
across restarts, which will make rate-limit tests behave unexpectedly.

---

## What is gunicorn, and why does it only matter in Docker?

Flask's own `app.run()` — the "development server" — is single-threaded by
default: it handles one request at a time, and Flask itself prints a warning
that it's not meant for production. **gunicorn** is a real WSGI server: it
runs several worker processes (`--workers 4` in the Dockerfiles) so multiple
requests are handled in parallel, and it restarts a worker automatically if
one crashes.

gunicorn depends on `fcntl`, a module that only exists on Unix/Linux — it
**cannot run natively on Windows at all**. That's fine, because:

- **Inside Docker**, the container is always Linux (even when Docker Desktop
  runs on a Windows host), so gunicorn works exactly as intended — this is
  what actually runs in `docker compose up`.
- **Running natively on Windows** (see below), you use Flask's own dev server
  instead. That's expected and fine for local debugging; it's simply never
  what ships in the container.

---

## Postman



## Postman Examples

<!-- Fill in with real request/response examples once the middleware is verified end-to-end. -->

### Request

```

```

### Response

```

```