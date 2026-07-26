import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "webhawk")
    DB_USER = os.getenv("DB_USER", "webhawk_user")
    # No fallback value here on purpose. Defaulting to an empty string would
    # let the service start and silently try to connect with no password,
    # instead of failing loudly with a clear error at startup.
    DB_PASSWORD = os.getenv("DB_PASSWORD")

    # No fallback value here on purpose. A hardcoded default would mean any
    # deployment that forgets to set a real secret in .env silently signs
    # and verifies every token with the exact same, publicly-visible value
    # sitting in this file - anyone who has ever read this code could forge
    # a valid token against that deployment. Every JWT this service issues
    # is only as safe as this secret, so a missing one has to stop the
    # service, not quietly weaken it.
    JWT_SECRET = os.getenv("JWT_SECRET")
    # Whatever is set in .env is used as-is; "HS256" only applies when the
    # variable is absent entirely. The value is validated below rather than
    # trusted blindly - see _require_supported_algorithm for why the set of
    # accepted values is deliberately narrow.
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    # Seconds, not minutes: the JWT spec defines the "exp" claim itself in
    # seconds, so this avoids converting units on the way in and back out
    # again. It also makes short values expressible - a 5-second expiry is
    # what an expiry test needs, and the smallest a minutes-based setting
    # could express is 60. Default 86400 = 24 hours.
    JWT_EXPIRY_SECS = int(os.getenv("JWT_EXPIRY_SECS", "86400"))
    
    # Used only by security_engine. Kept here rather than in that service so
    # there is exactly one place where any setting is read from the
    # environment, matching how DB_* and JWT_* are handled.
    RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "100"))
    # Seconds, matching the variable's name in .env. The SQL that uses this
    # passes it to make_interval(secs => ...) directly, so no unit conversion
    # happens anywhere - a conversion step is exactly where an off-by-60
    # error would hide.
    RATE_LIMIT_WINDOW_SECS = int(os.getenv("RATE_LIMIT_WINDOW_SECS", "60"))


def _require(name: str, value) -> None:
    """
    Stops the service immediately, with a clear message, if a genuinely
    sensitive setting was left unset - rather than letting it run on a
    silent, insecure fallback and fail confusingly (or not at all) later.
    """
    if not value:
        raise RuntimeError(
            f"{name} is not set. Copy .env.example to .env and set a real "
            f"value before starting this service - see the README's Setup "
            f"section."
        )


# Only symmetric HMAC algorithms are supported, because this project signs
# and verifies with a single shared secret (JWT_SECRET).
#
# Asymmetric algorithms (RS256, ES256, ...) are excluded deliberately, not
# by oversight: they need a private/public key pair rather than one shared
# string, so supporting them would require a different config shape
# entirely. Setting one here would make the code try to use JWT_SECRET as
# an RSA private key and fail with an opaque cryptography error.
#
# "none" is excluded for the same reason it's a classic JWT attack: a token
# with alg=none carries no signature at all, so anyone could forge one.
SUPPORTED_JWT_ALGORITHMS = ("HS256", "HS384", "HS512")


def _require_supported_algorithm(value: str) -> None:
    """
    Rejects an unsupported JWT_ALGORITHM at startup instead of at the first
    login attempt. Without this, a typo like "HS26" would let the service
    start normally and only surface when a real user tries to log in.
    """
    if value not in SUPPORTED_JWT_ALGORITHMS:
        raise RuntimeError(
            f"Unsupported JWT_ALGORITHM: {value!r}. "
            f"Supported values are: {', '.join(SUPPORTED_JWT_ALGORITHMS)}."
        )


def require_jwt_config() -> None:
    """
    Validates the JWT settings. Called at import time by jwt_utils, so it runs
    for the users service - the only one that signs or verifies tokens - and
    nowhere else.

    Deliberately NOT called at the bottom of this module: security_engine and
    backend_registry import Config for its DB settings but never touch JWT.
    Validating JWT_SECRET here unconditionally would mean those two services
    refuse to start over a secret they have no use for.
    """
    _require("JWT_SECRET", Config.JWT_SECRET)
    _require_supported_algorithm(Config.JWT_ALGORITHM)

# Checked for every importer of this module, since every service that imports
# Config at all does so to reach the database.
_require("DB_PASSWORD", Config.DB_PASSWORD)