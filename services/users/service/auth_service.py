from services.users.repository import user_repository, session_repository
from services.users.utils.password_utils import hash_password, verify_password
from services.users.utils.jwt_utils import generate_token, decode_token
from services.users.utils.constants import CLAIM_TOKEN_ID
from services.shared.exceptions import ServiceError


def register_user(email: str, password: str):
    """
    Creates a new user with a bcrypt-hashed password.
    Raises ServiceError(400) if input is missing, or (409) if email is taken.
    """
    if not email or not password:
        raise ServiceError("email and password are required", 400)

    if user_repository.get_user_by_email(email):
        raise ServiceError("a user with this email already exists", 409)

    password_hash = hash_password(password)
    return user_repository.create_user(email, password_hash)


def login_user(email: str, password: str, ip: str):
    """
    Verifies credentials, issues a JWT, and stores a matching active session.
    Raises ServiceError(400) on missing input, (401) on bad credentials.
    Returns (token, expires_at).
    """
    if not email or not password:
        raise ServiceError("email and password are required", 400)

    user = user_repository.get_user_by_email(email)
    if not user or not verify_password(password, user["password_hash"]):
        raise ServiceError("invalid email or password", 401)

    token, expires_at, jti = generate_token(user["id"], user["email"])
    session_repository.create_session(user["id"], jti, ip or "unknown", expires_at)

    return token, expires_at


def logout_user(token: str):
    """
    Revokes the session tied to this token's jti.
    Raises ServiceError(401) if the token itself is invalid/expired,
    or (404) if the session was already revoked / not found.
    """
    payload = decode_token(token)
    if not payload:
        raise ServiceError("invalid or expired token", 401)

    revoked = session_repository.revoke_session(payload[CLAIM_TOKEN_ID])
    if not revoked:
        raise ServiceError("session not found or already revoked", 404)


def validate_token(token: str):
    """
    Verifies the JWT signature/expiry AND checks the session is still active.
    Raises ServiceError(401) if either check fails.
    Returns the decoded JWT payload on success.
    """
    payload = decode_token(token)
    if not payload:
        raise ServiceError("invalid or expired token", 401)

    session = session_repository.get_active_session(payload[CLAIM_TOKEN_ID])
    if not session:
        raise ServiceError("session is not active", 401)

    return payload