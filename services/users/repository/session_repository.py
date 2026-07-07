from services.shared.connection import get_connection
from services.users.utils.constants import SESSION_STATUS_ACTIVE, SESSION_STATUS_REVOKED


def create_session(user_id: int, token_id: str, ip: str, expires_at):
    """
    Creates a new user session.

    Returns the ID of the created session.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_sessions (user_id, token_id, ip, expires_at, status)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (user_id, token_id, ip, expires_at, SESSION_STATUS_ACTIVE),
            )
            row = cur.fetchone()
            conn.commit()
            return row["id"]
    finally:
        conn.close()


def get_active_session(token_id: str):
    """
    Retrieves the active session matching the given token_id.

    Returns the session row if found, None otherwise.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM user_sessions
                WHERE token_id = %s AND status = %s AND expires_at > NOW()
                """,
                (token_id, SESSION_STATUS_ACTIVE),
            )
            return cur.fetchone()
    finally:
        conn.close()


def revoke_session(token_id: str) -> bool:
    """
    Marks the session matching token_id as revoked, if it's currently active.

    Returns True if a session was revoked, False if no matching active
    session was found (already revoked, or token_id doesn't exist).
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE user_sessions
                SET status = %s
                WHERE token_id = %s AND status = %s
                """,
                (SESSION_STATUS_REVOKED, token_id, SESSION_STATUS_ACTIVE),
            )
            updated = cur.rowcount
            conn.commit()
            return updated > 0
    finally:
        conn.close()