from services.shared.connection import get_connection


def get_user_by_email(email: str):
    """
    Retrieves a user by their email address.

    Returns the user row if found, None otherwise.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            return cur.fetchone()
    finally:
        conn.close()


def create_user(email: str, password_hash: str):
    """
    Creates a new user.

    Returns the created user row.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (email, password_hash)
                VALUES (%s, %s)
                RETURNING id, email, created_at
                """,
                (email, password_hash),
            )
            row = cur.fetchone()
            conn.commit()
            return row
    finally:
        conn.close()