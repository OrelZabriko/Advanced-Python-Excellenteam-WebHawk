from services.shared.connection import get_connection


def create_backend(service_name: str, target_url: str, api_key: str):
    """
    Creates a new backend registration.

    Returns the created row, including the generated api_key - this is the
    only place the raw key is ever read back from the database, matching
    how a real API key/secret is typically issued: shown once at creation.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO backend_registration (service_name, target_url, api_key)
                VALUES (%s, %s, %s)
                RETURNING id, service_name, target_url, api_key, active, created_at
                """,
                (service_name, target_url, api_key),
            )
            row = cur.fetchone()
            conn.commit()
            return row
    finally:
        conn.close()


def get_backend_by_api_key(api_key: str):
    """
    Retrieves a backend registration by its api_key.

    Returns the row if found, None otherwise. This is Contract B's lookup -
    the middleware calls it on every proxied request.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM backend_registration WHERE api_key = %s",
                (api_key,),
            )
            return cur.fetchone()
    finally:
        conn.close()


def get_all_backends():
    """
    Retrieves every registered backend.

    api_key is deliberately excluded from this query - a list view never
    returns raw keys, the same way a real secret/API key is normally
    handled. Returning it here would mean anyone with list access could
    read out every backend's live credential.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, service_name, target_url, active, created_at
                FROM backend_registration
                ORDER BY id
                """
            )
            return cur.fetchall()
    finally:
        conn.close()


def update_backend(backend_id: int, service_name: str, target_url: str) -> bool:
    """
    Updates a registration's service_name/target_url (not its api_key or
    active flag - see update_active_status for pausing/resuming).

    Returns True if a row was updated, False if no matching id was found.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE backend_registration
                SET service_name = %s, target_url = %s
                WHERE id = %s
                """,
                (service_name, target_url, backend_id),
            )
            updated = cur.rowcount
            conn.commit()
            return updated > 0
    finally:
        conn.close()


def update_active_status(backend_id: int, active: bool) -> bool:
    """
    Flips a registration's active flag - lets a developer pause/resume
    protection without deleting the registration.

    Returns True if a row was updated, False if no matching id was found.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE backend_registration SET active = %s WHERE id = %s",
                (active, backend_id),
            )
            updated = cur.rowcount
            conn.commit()
            return updated > 0
    finally:
        conn.close()