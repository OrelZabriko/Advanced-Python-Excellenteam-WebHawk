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

## How a request flows

Every request that reaches the middleware goes through four stages, in order.
Any stage can end the request early; only a request that passes all four is
forwarded to the real backend.

```
  client
    │  X-API-Key: whk_live_...
    │  Authorization: Bearer <jwt>
    ▼
┌─────────────────────────────────────────────┐
│ middleware  (catch-all route, no API of its │
│              own - it is a proxy)           │
└─────────────────────────────────────────────┘
    │
    │ 1. GET /backends/lookup?api_key=...      ──►  backend_registry
    │    Which backend does this key belong to,
    │    and is it currently active?
    │    ✗ unknown key → 404   ✗ paused → 403
    │
    │ 2. GET /validate                         ──►  users
    │    Is this JWT signed correctly, unexpired,
    │    and its session still un-revoked?
    │    ✗ missing / invalid → 401
    │
    │ 3. POST /analyze                         ──►  security_engine
    │    Does this request contain SQLi, XSS,
    │    or has this IP exceeded its rate limit?
    │    ✗ sqli / xss → 403   ✗ rate_limit → 429
    │
    │ 4. forward to target_url                 ──►  the real backend
    ▼
  the real backend's response, passed back verbatim
```

The middleware registers no routes of its own. `middleware/routes/proxy_routes.py`
installs a single catch-all (`/` plus `/<path:path>`, every method), so *every*
path and method that reaches it goes through the pipeline above.

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

- **Python 3.12** — [python.org/downloads](https://www.python.org/downloads/)
- **Docker Desktop** — [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/)
- **Git**

### On the Python version

All four `Dockerfile`s pin `FROM python:3.12-slim`, so 3.12 is what actually
runs in every container. Matching it locally means your editor checks your code
against the same version that will run it.

**Any 3.12.x patch release is fine** — 3.12.0, 3.12.10, whatever your OS
installs. The project uses no version-specific syntax (no `match`, no `X | Y`
type unions), so the patch number genuinely doesn't matter. Don't hunt for one
specific build.

#### Installing Python

| Environment | How |
|---|---|
| Windows (PowerShell or CMD) | Run the installer from python.org. **Tick "Add Python to PATH"** — without it, `python` is not found in a new terminal. |
| macOS | `brew install python@3.12` — the system Python is old and managed by Apple; don't use it. |
| Linux | `sudo apt install python3.12 python3.12-venv` (Debian/Ubuntu) |

#### `python` vs `python3`

On Windows the command is `python`. On macOS and Linux the command is
`python3` — plain `python` is either missing or points at Python 2.

This only matters **until the venv is activated**. Inside an active venv,
`python` works on every platform, which is why every command after Setup
step 2 below uses plain `python`.

#### Verify the installation

**PowerShell**
```powershell
python --version
docker --version
docker compose version
```

**Windows CMD**
```
python --version
docker --version
docker compose version
```

**macOS / Linux**
```bash
python3 --version
docker --version
docker compose version
```

---

## Setup

### 1. Clone

Identical in all three environments:

**PowerShell**
```powershell
git clone https://github.com/OrelZabriko/Advanced-Python-Excellenteam-WebHawk.git
cd Advanced-Python-Excellenteam-WebHawk
```

**Windows CMD**
```
git clone https://github.com/OrelZabriko/Advanced-Python-Excellenteam-WebHawk.git
cd Advanced-Python-Excellenteam-WebHawk
```

**macOS / Linux**
```bash
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
- Running a single service natively for debugging (see "Debugging a single
  service natively" below) runs it on your machine, not inside a container —
  it needs the venv active to find its dependencies.

All three steps, per environment. Steps 1 and 3 run **once**; step 2 has to be
repeated in **every new terminal session**.

**PowerShell**
```powershell
# 1. Create the venv (once, at the repo root)
python -m venv .venv

# 2. Activate it (every new terminal session)
.\.venv\Scripts\Activate.ps1

# 3. Install every dependency the project needs (once)
pip install -r requirements.txt
```

**Windows CMD**
```
REM 1. Create the venv (once, at the repo root)
python -m venv .venv

REM 2. Activate it (every new terminal session)
.\.venv\Scripts\activate.bat

REM 3. Install every dependency the project needs (once)
pip install -r requirements.txt
```

**macOS / Linux**
```bash
# 1. Create the venv (once, at the repo root)
python3 -m venv .venv

# 2. Activate it (every new terminal session)
source .venv/bin/activate

# 3. Install every dependency the project needs (once)
pip install -r requirements.txt
```

You'll know the venv is active because the prompt shows `(.venv)` at the start
of the line. Leave it active for every step below.

Note step 1 uses `python3` on macOS/Linux but `python` on Windows — that is the
`python` vs `python3` split described in Prerequisites. Steps 2 and 3, and
everything after this point, are the same everywhere, because an active venv
provides `python` and `pip` on all platforms.

**PowerShell only — if activation is blocked** with an execution-policy error,
allow it for the current session:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```
This affects only the current window and changes nothing system-wide. CMD and
macOS/Linux have no equivalent restriction.

> **What's actually in `requirements.txt`?** Flask (the web framework),
> psycopg2-binary (Postgres driver), bcrypt (password hashing), PyJWT (token
> signing), python-dotenv (`.env` loading), requests (the middleware's HTTP
> client to the other services), and gunicorn — see the callout below for
> what that last one is and why it only matters inside Docker.

### 3. Create your `.env`

All secrets and per-environment settings live in a single `.env` at the repo
root, which is **never committed**. Copy the template:

**PowerShell**
```powershell
Copy-Item .env.example .env
```

**Windows CMD**
```
copy .env.example .env
```

**macOS / Linux**
```bash
cp .env.example .env
```

Then open `.env` and set at minimum `DB_USER`, `DB_PASSWORD`, and `JWT_SECRET`.

Generate a real JWT secret rather than typing one — humans are bad at being
random, and every token the system signs is only as safe as this value:

**PowerShell**
```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Windows CMD**
```
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**macOS / Linux**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

This uses the Python you already installed, so it needs nothing extra and
behaves identically everywhere. `openssl rand -base64 32` produces an equally
good secret on macOS/Linux, but `openssl` is not present on Windows by
default — the Python one-liner avoids that split.

**`.env` syntax rule:** each line must be `KEY=VALUE`, with no spaces around
`=` and no trailing comment on a value line. `DB_HOST=postgres # docker` is
parsed as the literal value `postgres # docker` and breaks the connection.

### 4. Run everything

With the venv active and `.env` filled in:

**PowerShell**
```powershell
docker compose up --build
```

**Windows CMD**
```
docker compose up --build
```

**macOS / Linux**
```bash
docker compose up --build
```

This builds and starts every service on one Docker network, and initialises
Postgres automatically from the `.sql` files in `db/`.

### Resetting completely

Drops all users, registrations, logs and rate-limit counters. The `-v` flag is
what removes the Postgres volume — without it, old rows survive across
restarts, which will make rate-limit tests behave unexpectedly.

**PowerShell** — run as two separate commands. Windows PowerShell 5.1, the
version that ships with Windows, does not support `&&` and reports
"The token '&&' is not a valid statement separator". PowerShell 7 does support
it, but two lines work in both:
```powershell
docker compose down -v
docker compose up --build
```

**Windows CMD**
```
docker compose down -v && docker compose up --build
```

**macOS / Linux**
```bash
docker compose down -v && docker compose up --build
```

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
- **Running natively on Windows** (see "Debugging a single service
  natively" below), you use Flask's own dev server
  instead. That's expected and fine for local debugging; it's simply never
  what ships in the container.

---

## API reference

### middleware — `localhost:8080`

Accepts any path and any method. Two headers are required on every request.

| Header | Purpose |
|---|---|
| `X-API-Key` | Identifies which registered backend this request is for. |
| `Authorization: Bearer <jwt>` | Identifies the end user. Required with no exceptions. |

| Status | Meaning |
|---|---|
| `200` (or whatever the backend returns) | Allowed and forwarded. |
| `401` | Missing `X-API-Key`, missing `Authorization`, or invalid/revoked token. |
| `404` | The API key is not registered. |
| `403` | Blocked as `sqli`/`xss`, or the backend's protection is paused. |
| `429` | Blocked as `rate_limit`. |
| `500` | An internal service was unreachable or failed. |

A blocked response is deliberately generic — it names the `attack_type` but
never the specific rule that fired.

### backend_registry — `localhost:8083`

| Method | Path | Body | Returns |
|---|---|---|---|
| `POST` | `/backends` | `{service_name, target_url}` | `201` with the full registration **including `api_key`** |
| `GET` | `/backends/lookup?api_key=...` | — | `200` with `{found, service_name, target_url, active}` |
| `GET` | `/backends` | — | `200` with all registrations, **never including `api_key`** |
| `PUT` | `/backends/{id}` | `{service_name, target_url}` | `200`, or `404` if no such id |
| `PATCH` | `/backends/{id}/status` | `{active: true\|false}` | `200`, or `404` if no such id |

`GET /backends/lookup` returns `200` with `{"found": false}` for an unknown key
— not `404`. Per Contract B, "not found" is a normal business outcome for this
endpoint, not an HTTP error.

`PATCH .../status` is how a developer pauses protection without deleting the
registration. While paused, the middleware refuses requests for that backend
with `403`.

`target_url` must start with `http://` or `https://` — anything else is
rejected with `400`.

### users — `localhost:8082`

| Method | Path | Body / Header | Returns |
|---|---|---|---|
| `POST` | `/register` | `{email, password}` | `201`, or `409` if the email exists |
| `POST` | `/login` | `{email, password}` | `200` with `{token, expires_at}`, or `401` |
| `POST` | `/logout` | `Authorization: Bearer <jwt>` | `200`, or `404` if already revoked |
| `GET` | `/validate` | `Authorization: Bearer <jwt>` | `200` with `{valid, user_id, email}`, or `401` |

Wrong password and unknown email both return the same `401` message. This is
deliberate — a different message for each would let anyone enumerate which
email addresses are registered.

`/validate` checks more than the JWT's own signature and expiry: it also
confirms the matching row in `user_sessions` is still `active`. That is what
makes `/logout` meaningful — a token can be invalidated before it naturally
expires, which a signature check alone could never do.

### security_engine — `localhost:8081`

| Method | Path | Returns |
|---|---|---|
| `POST` | `/analyze` | `200` with a verdict, or `400` if malformed |

Note `/analyze` always returns `200` when it can evaluate the request — the
verdict is in the body, not the status code. It is the *middleware* that turns
a `{"allowed": false}` verdict into a `403`/`429` for the client.

Request body (Contract A):

```json
{
  "endpoint": "/api/search",
  "method": "POST",
  "ip": "172.18.0.1",
  "headers": {},
  "query_params": {},
  "path_params": {},
  "body": {"q": "hello"}
}
```

`endpoint`, `method` and `ip` are required; the rest are scanned if present.
Every string value found anywhere in `query_params`, `path_params` and `body`
is checked, at any nesting depth.

Response:

```json
{"allowed": true, "attack_type": null, "reason": null}
```

`attack_type` and `reason` are **always present** — as explicit `null` on a
clean request, never omitted. The middleware relies on that guarantee, so a
missing key and an explicit `null` are not interchangeable here.

---

## Security notes

- **Passwords are hashed with bcrypt** (`services/users/utils/password_utils.py`),
  not a fast hash like SHA-256. bcrypt's built-in per-password salt and
  deliberately slow cost factor are what make hashes resistant to brute-force
  and rainbow-table attacks.
- **All SQL uses parameterised queries** (`%s` placeholders passed to
  `cur.execute`). No query in this project is built by string concatenation —
  which matters more than usual here, given that the whole point of the product
  is blocking SQL injection.
- **API keys are shown exactly once**, at creation time (`POST /backends`).
  `GET /backends` never returns `api_key` for any registration — otherwise
  anyone with list access could read out every backend's live credential. The
  key itself is `secrets.token_hex(16)` — 128 bits from the OS's cryptographic
  random source, not Python's `random` module, which is deterministic and
  unsuitable for anything security-sensitive.
- **The middleware identifies the target backend via an `X-API-Key` header.**
  This is a judgment call, not a locked-in team decision: the API Contracts doc
  defines the *lookup* (Contract B: given an api_key, find the target) but not
  how that key travels on the request.
- **A valid `Authorization` header is required on every proxied request**, with
  no exceptions. Skipping the check when the header is absent would let anyone
  bypass authentication entirely just by omitting it.
- **Every internal HTTP call has an explicit 5-second timeout**
  (`INTERNAL_CALL_TIMEOUT_SECS` in `middleware/clients/service_endpoints.py`).
  `requests` has **no** default timeout — without an explicit value, one hung
  service or one slow real backend would tie up the request indefinitely
  instead of failing fast with a 500.
- **Internal error details never reach the client.** A failed internal call is
  logged server-side with its context ("security_engine unreachable"), but the
  client always receives the same generic 500. Putting the context in the
  response body would let anyone who can trigger a 500 map the internal service
  topology.
- **Hop-by-hop headers are stripped from the forwarded response.**
  `Content-Encoding`, `Content-Length` and friends describe how *one* hop was
  framed. `requests` already decompresses a gzipped backend response, so
  passing `Content-Encoding: gzip` through would make the client try to
  decompress plain text. Any real backend behind nginx or a CDN gzips by
  default, so this is the common case, not an edge case.
- **`user_sessions.token_id` stores the JWT's `jti` claim, not the token
  itself.** A `jti` is a UUID — always 36 characters, so `VARCHAR(255)` has
  ample room. Storing whole tokens instead would mean anyone with read access
  to that table holds working credentials for every logged-in user.
- **Every JWT carries a random `jti` claim.** Without it, two logins by the
  same user within the same second could produce a byte-identical token,
  colliding with the `UNIQUE` constraint on `user_sessions.token_id` and
  turning a valid login into a 500.
- **Every service installs global error handlers**
  (`register_error_handlers` in each `app.py`, from
  `services/shared/error_handlers.py`). These guarantee every response carries
  a JSON body — including the 404/405 Flask raises before routing, and any
  exception a route did not anticipate. Exception text is logged server-side
  and never returned, since a psycopg2 error routinely contains the database
  host, port and user.
- **The users service refuses to start without `JWT_SECRET`**
  (`require_jwt_config()` in `services/shared/config.py`, called from
  `jwt_utils.py`). It does not fall back to a guessable default. If you see
  `RuntimeError: JWT_SECRET is not set` in `docker compose logs users`,
  generate one:
  ```
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
- **Same fail-fast applies to `JWT_ALGORITHM`** — only `HS256`, `HS384` and
  `HS512` are supported. Anything else, including asymmetric algorithms like
  `RS256`, makes users refuse to start. Asymmetric algorithms need a
  public/private key pair rather than the single shared secret this project
  uses, so supporting them would require a different config shape entirely.
- **`security_engine` and `backend_registry` deliberately do *not* require
  `JWT_SECRET`.** They import `Config` for its database settings but never
  touch JWT, so validating a secret they have no use for would be a confusing
  failure that says nothing about what is actually wrong.

---

## Configuration

Every variable, from `.env.example`:

```
DB_HOST=postgres
DB_PORT=5432
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=webhawk
JWT_SECRET=change_this_secret
JWT_ALGORITHM=HS256
JWT_EXPIRY_SECS=86400
RATE_LIMIT_MAX_REQUESTS=100
RATE_LIMIT_WINDOW_SECS=60
```

All of it is read in one place — `services/shared/config.py` — by
`python-dotenv`'s `load_dotenv()`, which injects each line into `os.environ`;
`Config` then reads them with `os.getenv`. Which settings each service
actually *uses*:

| Setting | Used by |
|---|---|
| `DB_*` | users, security_engine, backend_registry |
| `JWT_*` | users only |
| `RATE_LIMIT_*` | security_engine only |

The middleware appears in none of these rows: it has no database and reads no
environment variables at all. The three internal service addresses it needs
are constants in `middleware/clients/service_endpoints.py`, because they are
structural facts about how Compose wires the network together, not
per-environment settings.

**`DB_HOST=postgres`** because the project runs under Docker Compose by
default — `postgres` is the Compose service name, resolved by Docker's
internal DNS. Override it to `127.0.0.1` only if you are running a service
natively for debugging.

**`.env` is read by two independent mechanisms.** First, `load_dotenv()` in
`config.py`, used by each Flask service at runtime. Second, **Docker Compose
itself**, which substitutes `${VAR}` anywhere in `docker-compose.yml` from a
file literally named `.env` at the repo root — a built-in Compose feature, not
something this project added. That is how `postgres`'s own
`POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB` avoid being hardcoded.

**`.env` syntax rule:** each line must be `KEY=VALUE` only — no spaces around
`=`, no trailing comment on a value line. Because two different parsers read
this file (python-dotenv and Compose's own Go parser), and they do not agree
in the edge cases, the safe rule is the intersection: plain `KEY=VALUE`, with
comments only on their own lines.

**`.dockerignore`** (repo root) exists so `.env` never gets baked into an
image. `.gitignore` only controls what goes into *git* — it has no effect on
what `COPY` puts inside an image.

**Line endings:** `.gitattributes` forces `eol=lf` on all text files. A
Windows-saved `.env` with CRLF leaves a trailing `\r` inside a value, so
`DB_HOST` becomes `postgres\r` and the connection fails with an error that
looks nothing like a line-ending problem.

### Why `RATE_LIMIT_WINDOW_SECS` stays in seconds

The window is applied directly in seconds all the way through `Config` →
`SecurityRepository` → SQL (`make_interval(secs => ...)`). No conversion to
minutes happens anywhere.

`make_interval`'s `mins` parameter only accepts whole integers, so expressing
the window in minutes would force integer division somewhere — and that
rounding is silent:

- `RATE_LIMIT_WINDOW_SECS=90` → `90 / 60 = 1` minute → real window silently
  becomes **60 seconds**: weaker than configured.
- `RATE_LIMIT_WINDOW_SECS=30` → `30 / 60 = 0` → real window silently becomes
  **no window at all**, disabling rate limiting entirely.

Either way a variable named `..._SECS` would claim one thing and enforce
another, with no way to tell from reading `.env`.

---

## Database

Schema lives in `db/` as plain `.sql` files, loaded automatically by the
`postgres` container on first start (via `docker-entrypoint-initdb.d`).

| Table | Owner | Purpose |
|---|---|---|
| `users` | users | One row per account. `password_hash` holds a bcrypt hash, which embeds its own salt — no separate salt column needed. |
| `user_sessions` | users | One row per login. Lets a JWT be revoked before it expires. |
| `backend_registration` | backend_registry | One row per protected backend. `api_key` is `UNIQUE`, which also gives lookups their index for free. |
| `logs_security` | security_engine | Audit trail of every analysed request, clean or blocked. |
| `limit_rate` | security_engine | Running request counter per IP per endpoint. `UNIQUE(ip, endpoint)` means one row per pair, updated in place. |

The whole `db/` folder is mounted at once, so Postgres runs the files in
alphabetical order. That is safe here because no table references another with
a foreign key.

Because the schema files only run on **first** start, editing a `.sql` file has
no effect on an existing volume. Use `docker compose down -v` to force a
reload.

---

## Debugging a single service natively (optional)

Only needed to run one service directly on your machine, outside Docker, for
faster iteration with a debugger attached — not the normal way to use the
project.

Step 3 is an edit to `.env`, not a command: set `DB_HOST=127.0.0.1` instead of
`postgres`, because the service now runs outside the Docker network and cannot
resolve the `postgres` hostname.

**PowerShell**
```powershell
# 1. Start only the database
docker compose up -d postgres

# 2. Activate the venv
.\.venv\Scripts\Activate.ps1

# 4. Run from the REPO ROOT, as a module
python -m services.users.app
```

**Windows CMD**
```
REM 1. Start only the database
docker compose up -d postgres

REM 2. Activate the venv
.\.venv\Scripts\activate.bat

REM 4. Run from the REPO ROOT, as a module
python -m services.users.app
```

**macOS / Linux**
```bash
# 1. Start only the database
docker compose up -d postgres

# 2. Activate the venv
source .venv/bin/activate

# 4. Run from the REPO ROOT, as a module
python -m services.users.app
```

Run it as a **module** (`python -m services.users.app`) from the repo root, not
by `cd`-ing into the folder and running `app.py` directly. The repo root has to
be on `sys.path` for `services.shared.config` to resolve, and `python -m` puts
it there automatically.

Every service listens on 8080, hardcoded in its own `app.py`. Outside Docker
there is no container isolation, so **only run one service natively at a
time** — a second would fail to bind to the same port.

`gunicorn` will not work here (it depends on `fcntl`, which is Unix-only), so
this runs Flask's own development server. That is exactly what you want for
native debugging, and it is never what ships in the container.

---

## Postman

Collections live in `postman/`, exported once each flow below is confirmed
working. The tests are numbered by service so a failure points at one place:
`1.x` backend_registry, `2.x` users, `3.x` security_engine, `4.x` the full
pipeline through the middleware.

Run them in order — `1.1` produces the `api_key` that `4.x` needs, and `2.3`
produces the `token`. In Postman, save both as **collection variables** so
`{{api_key}}` and `{{token}}` resolve in later requests.

**A note on `target_url`.** The middleware forwards allowed requests to
whatever `target_url` the backend was registered with, so that URL has to
actually answer or step 4 has nothing to reach. There is no dedicated demo
backend in this project, so the simplest working choice is another service on
the same Docker network — `http://users:8080` — which means a request to
`/validate` through the middleware ends up at `http://users:8080/validate`.
Note it must be the *internal* address (`users:8080`), not `localhost:8082`:
the middleware resolves this from inside the Docker network.

## Postman Examples

### backend_registry Tests
#### Test 1.1
##### Request
- Method: POST
- URL: ``` http://localhost:8083/backends ```
- Headers:
    KEY: ``` Content-Type ```
    VALUE: ``` application/json ```
- Body:
  ```
    {
      "service_name": "google-api",
      "target_url": "http://users:8080"
    }
  ```
- Save the api_key you will get in the result!

##### Response
- status: ``` 201 Created ```
-
```json
  {
    "active": true,
    "api_key": "whk_live_e09a695d1bc554d57f737fa4610af51d",
    "created_at": "2026-07-26T07:36:37.649938+00:00",
    "id": 1,
    "service_name": "google-api",
    "target_url": "http://demo-backend:8080"
  }
```


#### Test 1.2
##### Request
- Method: GET
- URL: ``` http://localhost:8083/backends/lookup?api_key={{api_key}} ```

##### Response
- status: ``` 200 OK ```
-
```json
  {"active": true, "found": true, "service_name": "google-api", "target_url": "http://demo-backend:8080"}
```


#### Test 1.3
##### Request
- Method: GET
- URL: ``` http://localhost:8083/backends/lookup?api_key=whk_live_doesnotexist ```

##### Response
- status: ``` 200 OK ```
-
```json
  {"found": false}
```
- Confirms an unknown key returns `200` with `found: false`, not a `404` —
  "not found" is a normal business outcome here, per Contract B.


#### Test 1.4
##### Request
- Method: GET
- URL: ``` http://localhost:8083/backends ```
- Confirm `api_key` does NOT appear in the response.

##### Response
- status: ``` 200 OK ```
-
```json
  {
    "backends": [
      {"active": true, "created_at": "2026-07-26T07:36:37.649938+00:00", "id": 1, "service_name": "google-api", "target_url": "http://demo-backend:8080"},
      {"active": true, "created_at": "2026-07-26T07:49:47.311787+00:00", "id": 2, "service_name": "google-api", "target_url": "http://demo-backend:8080"}
    ]
  }
```
- Confirmed: `api_key` does NOT appear in either entry, as expected.


#### Test 1.5
##### Request
- Method: PUT
- URL: ``` http://localhost:8083/backends/1 ```
- Headers:
    KEY: ``` Content-Type ```
    VALUE: ``` application/json ```
- Body:
  ```
    {
      "service_name": "google-api-v2",
      "target_url": "http://users:8080"
    }
  ```

##### Response
- status: ``` 200 OK ```
-
```json
  {"id": 1, "message": "backend updated successfully", "service_name": "google-api-v2", "target_url": "http://demo-backend:8080"}
```


#### Test 1.6
##### Request
- Method: POST
- URL: ``` http://localhost:8083/backends ```
- Headers:
    KEY: ``` Content-Type ```
    VALUE: ``` application/json ```
- Body:
  ```
    {
      "service_name": "broken"
    }
  ```

##### Response
- status: ``` 400 Bad Request ```
-
```json
  {"error": "service_name and target_url are required"}
```


#### Test 1.7
##### Request
- Method: POST
- URL: ``` http://localhost:8083/backends ```
- Headers:
    KEY: ``` Content-Type ```
    VALUE: ``` application/json ```
- Body:
  ```
    {
      "service_name": "bad",
      "target_url": "users:8080"
    }
  ```

##### Response
- status: ``` 400 Bad Request ```
-
```json
  {"error": "target_url must start with http:// or https://"}
```


#### Test 1.8
##### Request
- Method: PUT
- URL: ``` http://localhost:8083/backends/9999 ```
- Headers:
    KEY: ``` Content-Type ```
    VALUE: ``` application/json ```
- Body:
  ```
    {
      "service_name": "x",
      "target_url": "http://x:8080"
    }
  ```

##### Response
- status: ``` 404 Not Found ```
-
```json
  {"error": "backend registration not found"}
```


#### Test 1.9
##### Request
- Method: GET
- URL: ``` http://localhost:8083/no-such-endpoint ```
- Confirms the global error handler returns JSON, not an HTML error page.

##### Response
- status: ``` 404 Not Found ```
-
```json
  {"error": "The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again."}
```
- Confirms the global error handler returns JSON here, not Flask's default
  HTML error page — this is what a custom `@app.errorhandler(404)` produces.


### users Tests
#### Test 2.1
##### Request
- Method: POST
- URL: ``` http://localhost:8082/register ```
- Headers:
    KEY: ``` Content-Type ```
    VALUE: ``` application/json ```
- Body:
  ```
    {
      "email": "test@test.com",
      "password": "Secret123!"
    }
  ```

##### Response
- status: ``` 201 Created (fresh database) ```
-
```json
  {"email": "test@test.com", "id": 1}
```
- Note: if this email is already registered (e.g. from a previous test run
  against the same database), this returns `409` with
  `{"error": "a user with this email already exists"}` instead — that is
  Test 2.2's expected behavior, not a bug. Reset the database
  (`docker compose down -v`) before a full re-run if you want a clean `201` here.


#### Test 2.2
##### Request
- Method: POST
- URL: ``` http://localhost:8082/register ```
- Headers:
    KEY: ``` Content-Type ```
    VALUE: ``` application/json ```
- Body:
  ```
    {
      "email": "test@test.com",
      "password": "Secret123!"
    }
  ```

##### Response
- status: ``` 409 Conflict ```
-
```json
  {"error": "a user with this email already exists"}
```


#### Test 2.3
##### Request
- Method: POST
- URL: ``` http://localhost:8082/login ```
- Headers:
    KEY: ``` Content-Type ```
    VALUE: ``` application/json ```
- Body:
  ```
    {
      "email": "test@test.com",
      "password": "Secret123!"
    }
  ```
- Save the token you will get in the result!

##### Response
- status: ``` 200 OK ```
-
```json
  {
    "expires_at": "2026-07-27T07:49:49.415298+00:00",
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJlbWFpbCI6InRlc3RAdGVzdC5jb20iLCJqdGkiOiI2YWYyZTVmYy0zZDJmLTQ1OGUtODgyNy01MGNhZjJmMzZhODciLCJpYXQiOjE3ODUwNTIxODksImV4cCI6MTc4NTEzODU4OX0.lWWP159IobVhqSrZCOdx8q38ewJZbsRafdXjM0oJWIk"
  }
```


#### Test 2.4
##### Request
- Method: POST
- URL: ``` http://localhost:8082/login ```
- Headers:
    KEY: ``` Content-Type ```
    VALUE: ``` application/json ```
- Body:
  ```
    {
      "email": "test@test.com",
      "password": "wrong"
    }
  ```
- Compare the message with Test 2.4b - they must be identical.

##### Response
- status: ``` 401 Unauthorized ```
-
```json
  {"error": "invalid email or password"}
```


#### Test 2.4b
##### Request
- Method: POST
- URL: ``` http://localhost:8082/login ```
- Headers:
    KEY: ``` Content-Type ```
    VALUE: ``` application/json ```
- Body:
  ```
    {
      "email": "nosuchuser@test.com",
      "password": "Secret123!"
    }
  ```

##### Response
- status: ``` 401 Unauthorized ```
-
```json
  {"error": "invalid email or password"}
```
- Confirmed identical to Test 2.4's response — same message, same status,
  for both "wrong password" and "email doesn't exist." This is what prevents
  email enumeration via the login endpoint.


#### Test 2.5
##### Request
- Method: GET
- URL: ``` http://localhost:8082/validate ```
- Headers:
    KEY: ``` Authorization ```
    VALUE: ``` Bearer {{token}} ```

##### Response
- status: ``` 200 OK ```
-
```json
  {"email": "test@test.com", "user_id": 1, "valid": true}
```


#### Test 2.6
##### Request
- Method: GET
- URL: ``` http://localhost:8082/validate ```

##### Response
- status: ``` 401 Unauthorized ```
-
```json
  {"error": "missing bearer token", "valid": false}
```

#### Test 2.7
##### Request
- Method: POST
- URL: ``` http://localhost:8082/logout ```
- Headers:
    KEY: ``` Authorization ```
    VALUE: ``` Bearer {{token}} ```

##### Response
- status: ``` 200 OK ```
-
```json
  {"message": "logged out"}
```


#### Test 2.8
##### Request
- Method: GET
- URL: ``` http://localhost:8082/validate ```
- Headers:
    KEY: ``` Authorization ```
    VALUE: ``` Bearer {{token}} ```
- The same token that worked in 2.5. It must now fail - that is what proves
  logout revokes a token before it naturally expires.

##### Response
- status: ``` 401 Unauthorized ```
-
```json
  {"error": "session is not active", "valid": false}
```
- Confirms the token that passed validation in Test 2.5 is now correctly
  rejected — even though the JWT itself hasn't naturally expired yet, the
  underlying session was revoked by logout. This is the whole point of
  tracking sessions server-side rather than relying on JWT expiry alone.


### security_engine Tests

Note: `/analyze` returns `200` for every request it can evaluate — the verdict
is in the body (`"allowed": true/false`), not the status code.

#### Test 3.1
##### Request
- Method: POST
- URL: ``` http://localhost:8081/analyze ```
- Headers:
    KEY: ``` Content-Type ```
    VALUE: ``` application/json ```
- Body:
  ```
    {
      "endpoint": "/api/clean-test",
      "method": "POST",
      "ip": "10.0.0.1",
      "headers": {"User-Agent": "curl"},
      "query_params": {},
      "path_params": {},
      "body": {"username": "orel"}
    }
  ```
- Confirm `attack_type` and `reason` are present as explicit `null`.

##### Response
- status: ``` 200 OK ```
-
```json
  {"allowed": true, "attack_type": null, "reason": null}
```
- Confirms `attack_type` and `reason` are present as explicit `null` on a
  clean request, not omitted — the middleware relies on this guarantee.


#### Test 3.2
##### Request
- Method: POST
- URL: ``` http://localhost:8081/analyze ```
- Headers:
    KEY: ``` Content-Type ```
    VALUE: ``` application/json ```
- Body:
  ```
    {
      "endpoint": "/api/sqli-test",
      "method": "POST",
      "ip": "10.0.0.2",
      "headers": {},
      "query_params": {},
      "path_params": {},
      "body": {"username": "admin' OR 1=1 --"}
    }
  ```

##### Response
- status: ``` 200 OK ```
-
```json
  {"allowed": false, "attack_type": "sqli", "reason": "SQL injection pattern detected"}
```


#### Test 3.3
##### Request
- Method: POST
- URL: ``` http://localhost:8081/analyze ```
- Headers:
    KEY: ``` Content-Type ```
    VALUE: ``` application/json ```
- Body:
  ```
    {
      "endpoint": "/api/xss-test",
      "method": "POST",
      "ip": "10.0.0.3",
      "headers": {},
      "query_params": {"q": "<script>alert(1)</script>"},
      "path_params": {},
      "body": {}
    }
  ```

##### Response
- status: ``` 200 OK ```
-
```json
  {"allowed": false, "attack_type": "xss", "reason": "XSS pattern detected"}
```


#### Test 3.4
##### Request
- Method: POST
- URL: ``` http://localhost:8081/analyze ```
- Headers:
    KEY: ``` Content-Type ```
    VALUE: ``` application/json ```
- Body:
  ```
    {
      "endpoint": "/api/nested-test",
      "method": "POST",
      "ip": "10.0.0.4",
      "headers": {},
      "query_params": {},
      "path_params": {},
      "body": {"user": {"profile": {"bio": "<script>alert(1)</script>"}}}
    }
  ```
- Proves the scan reaches strings at any nesting depth, not just top level.

##### Response
- status: ``` 200 OK ```
-
```json
  {"allowed": false, "attack_type": "xss", "reason": "XSS pattern detected"}
```
- Confirms the scanner reaches strings at any nesting depth, not just top-level
  fields — the XSS payload here is three levels deep (`body.user.profile.bio`).

#### Test 3.5
##### Request
- Method: POST
- URL: ``` http://localhost:8081/analyze ```
- Headers:
    KEY: ``` Content-Type ```
    VALUE: ``` application/json ```
- Body: send this the number of times set in `RATE_LIMIT_MAX_REQUESTS` plus one
  (default 101). Postman's Collection Runner with an iteration count is the
  easiest way.
  ```
    {
      "endpoint": "/api/rate-test",
      "method": "GET",
      "ip": "10.0.0.99",
      "headers": {},
      "query_params": {},
      "path_params": {},
      "body": {}
    }
  ```

##### Response
- status: ``` 200 OK (both, per Contract A — verdict is in the body) ```
-
  Request #100 (still under the limit):
```json
  {"allowed": true, "attack_type": null, "reason": null}
```

  Request #101 (over the limit):
```json
  {"allowed": false, "attack_type": "rate_limit", "reason": "Rate limit exceeded for this IP"}
```
- Confirmed: `RATE_LIMIT_MAX_REQUESTS` default of 100 works exactly as
  documented — the 100th request still passes, the 101st is blocked.
  `/analyze` itself returns `200` in both cases; it's the *middleware*
  that would translate a blocked verdict into a client-facing `429`.


#### Test 3.6
##### Request
- Method: POST
- URL: ``` http://localhost:8081/analyze ```
- Headers:
    KEY: ``` Content-Type ```
    VALUE: ``` application/json ```
- Body:
  ```
    {
      "method": "GET"
    }
  ```
- Missing the required `endpoint` and `ip` fields.

##### Response
- status: ``` 400 Bad Request ```
-
```json
  {"error": "Missing required fields: endpoint, method, ip"}
```

### middleware Tests
#### Test 4.1
##### Request
- Method: GET
- URL: ``` http://localhost:8080/api/anything ```
- No headers at all.
- Tests the real middleware pipeline (not `/validate` in isolation) — this
  hits the middleware's catch-all proxy route directly.

##### Response
- status: ``` 401 Unauthorized ```
-
```json
  {"error": "Missing X-API-Key header"}
```

#### Test 4.2
##### Request
- Method: GET
- URL: ``` http://localhost:8080/api/anything ```
- Headers:
    KEY: ``` X-API-Key ```
    VALUE: ``` whk_live_fake123 ```

##### Response
- status: ``` 404 Not Found ```
-
```json
  {"error": "Unknown API key"}
```


##### Request
- Method: GET
- URL: ``` http://localhost:8080/api/anything ```
- Headers:
    KEY: ``` X-API-Key ```
    VALUE: ``` {{api_key}} ```
- Valid key, but no Authorization header.

##### Response
- status: ``` 401 Unauthorized ```
-
```json
  {"error": "Authorization header required"}
```


#### Test 4.4
##### Request
- Method: GET
- URL: ``` http://localhost:8080/api/anything ```
- Headers:
    KEY-1: ``` X-API-Key ```
    VALUE-1: ``` {{api_key}} ```
    KEY-2: ``` Authorization ```
    VALUE-2: ``` Bearer {{token}} ```

##### Response
- status: ``` 401 Unauthorized ```
-
```json
  {"error": "Invalid or expired token"}
```
- Note: this result reflects `{{token}}` having been revoked earlier by
  Test 2.7's logout — the middleware correctly propagates the users
  service's session-revocation check through the full pipeline. Log in
  again (Test 2.3) to refresh `{{token}}` with an active session before
  running Test 4.5 onward, which expect a valid, non-revoked token.


#### Test 4.5
##### Request
- Method: POST
- URL: ``` http://localhost:8080/api/users/profile ```
- Headers:
    KEY-1: ``` X-API-Key ```
    VALUE-1: ``` {{api_key}} ```
    KEY-2: ``` Authorization ```
    VALUE-2: ``` Bearer {{token}} ```
    KEY-3: ``` Content-Type ```
    VALUE-3: ``` application/json ```
- Body:
{
  "name": "Oren",
  "city": "Jerusalem"
}
- The full happy path: forwarded to `http://users:8080/validate`. The response
  you see is the users service's own, passed through unchanged.
- If you ran Test 2.7 (logout), log in again first - that token is revoked.

##### Response
- status: ``` 500 Internal Server Error ```
-
```json
  {"error": "Internal server error"}
```
- This `500` is expected in the current setup, not a failure. The
  registration in Test 1.1 points `target_url` at `http://demo-backend:8080`,
  and no such service exists in `docker-compose.yml` - so stage 4 has nothing
  to forward to. Stages 1-3 (api_key lookup, JWT validation, security
  analysis) all passed; only the final hop failed.
- To see this return `200`, register a backend whose `target_url` points at
  any HTTP service running on the Docker network, then re-run with that
  `api_key`.


#### Test 4.6
##### Request
- Method: POST
- URL: ``` http://localhost:8080/api/users/search ```
- Headers:
    KEY-1: ``` X-API-Key ```
    VALUE-1: ``` {{api_key}} ```
    KEY-2: ``` Authorization ```
    VALUE-2: ``` Bearer {{token}} ```
    KEY-3: ``` Content-Type ```
    VALUE-3: ``` application/json ```
- Body:
  ```
    {
      "query": "admin' OR 1=1 --"
    }
  ```
- Confirm the response contains `attack_type` but NOT `reason`.

##### Response
- status: ``` 403 Forbidden ```
-
```json
  {"attack_type": "sqli", "error": "Request blocked"}
```
- Confirmed: `attack_type` is present, but `reason` is deliberately absent —
  the middleware doesn't expose which specific rule fired, unlike
  `security_engine`'s own `/analyze` response (Test 3.2), which does include
  a `reason`. This prevents an attacker from learning the exact detection
  logic through trial and error.

  ```


#### Test 4.7
##### Request
- Method: GET
- URL: ``` http://localhost:8080/api/comments?text=<script>alert(1)</script> ```
- Headers:
    KEY-1: ``` X-API-Key ```
    VALUE-1: ``` {{api_key}} ```
    KEY-2: ``` Authorization ```
    VALUE-2: ``` Bearer {{token}} ```

##### Response
- status: ``` 403 Forbidden ```
-
```json
  {"attack_type": "xss", "error": "Request blocked"}
```
- Confirms the scan reaches query parameters, not just JSON bodies — and
  again, `reason` is correctly omitted from the middleware's client-facing
  response.


#### Test 4.8
##### Request
- Method: GET
- URL: ``` http://localhost:8080/api/ratelimit-e2e ```
- Headers:
    KEY-1: ``` X-API-Key ```
    VALUE-1: ``` {{api_key}} ```
    KEY-2: ``` Authorization ```
    VALUE-2: ``` Bearer {{token}} ```
- Send this the number of times set in `RATE_LIMIT_MAX_REQUESTS` plus one
  (default 101), through the full middleware pipeline this time, not
  directly against `security_engine`. Postman's Collection Runner with an
  iteration count is the easiest way.
- Requires the registered backend's `target_url` to point at a real,
  reachable service (e.g. `http://users:8080`) - see Test 4.5's note.
  Otherwise every request fails with `500` before it ever reaches the
  rate limiter.

##### Response
- status: ``` 404 (requests 1-100) / 429 (request 101) ```
-
  Early request (still under the limit — proxied all the way through to the
  real backend, which has no matching route):
```json
  {"error": "The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again."}
```

  Request #101 (over the limit):
```json
  {"attack_type": "rate_limit", "error": "Request blocked"}
```
- Confirms the middleware correctly translates a rate-limit verdict into a
  real `429` for the client — unlike `security_engine`'s own `/analyze`
  (Test 3.5), which always returns `200` with the verdict in the body.


#### Test 4.9.1
##### Request
- Method: PATCH
- URL: ``` http://localhost:8083/backends/1/status ```
- Headers:
    KEY: ``` Content-Type ```
    VALUE: ``` application/json ```
- Body:
  ```
    {
      "active": false
    }
  ```

##### Response
- status: ``` 200 OK ```
-
```json
  {"active": false, "id": 1, "message": "status updated successfully"}
```

  ```


#### Test 4.9.2
##### Request
- Method: GET
- URL: ``` http://localhost:8080/validate ```
- Headers:
    KEY-1: ``` X-API-Key ```
    VALUE-1: ``` {{api_key}} ```
    KEY-2: ``` Authorization ```
    VALUE-2: ``` Bearer {{token}} ```
- Same request as 4.5, but the backend is now paused.

##### Response
- status: ``` 403 Forbidden ```
-
```json
  {"error": "This backend's protection is currently paused"}
```
- Confirms a paused backend is blocked at stage 1 (backend_registry lookup)
  - before the request ever reaches users, security_engine, or the real
  backend. Same request as Test 4.5, different result purely because of
  the backend's active/paused status.


#### Test 4.9.3
##### Request
- Method: PATCH
- URL: ``` http://localhost:8083/backends/1/status ```
- Headers:
    KEY: ``` Content-Type ```
    VALUE: ``` application/json ```
- Body:
  ```
    {
      "active": true
    }
  ```
- Re-enable, so the collection can be re-run from the start.

##### Response
- status: ``` 200 OK ```
-
```json
  {"active": true, "id": 1, "message": "status updated successfully"}
```
- Backend re-enabled - the collection can now be re-run from the start.