# Encoding
ENCODING = "utf-8"

# JWT claim names
CLAIM_USER_ID = "user_id"
CLAIM_EMAIL = "email"
CLAIM_ISSUED_AT = "iat"   # standard JWT claim — PyJWT recognizes this name
CLAIM_EXPIRES_AT = "exp"  # standard JWT claim — PyJWT auto-validates this name

# Session status values (matches user_sessions.status CHECK constraint)
SESSION_STATUS_ACTIVE = "active"
SESSION_STATUS_REVOKED = "revoked"