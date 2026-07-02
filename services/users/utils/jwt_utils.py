import jwt
import datetime
from services.shared.config import Config
from services.users.utils.constants import CLAIM_USER_ID, CLAIM_EMAIL, CLAIM_ISSUED_AT, CLAIM_EXPIRES_AT


def generate_token(user_id: int, email: str):
    """Returns (token_string, expires_at_datetime)."""
    now = datetime.datetime.utcnow()
    expires_at = now + datetime.timedelta(minutes=Config.JWT_EXPIRY_MINUTES)

    payload = {
        CLAIM_USER_ID: user_id,
        CLAIM_EMAIL: email,
        CLAIM_ISSUED_AT: now,
        CLAIM_EXPIRES_AT: expires_at,
    }

    token = jwt.encode(payload, Config.JWT_SECRET, algorithm=Config.JWT_ALGORITHM)
    return token, expires_at


def decode_token(token: str):
    """
    Returns the decoded payload dict, or None if invalid/expired.
    Never raises — callers just check for None.
    """
    try:
        return jwt.decode(token, Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None