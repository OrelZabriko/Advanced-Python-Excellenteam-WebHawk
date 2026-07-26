from services.shared.config import Config
from services.shared.connection import get_connection


class SecurityRepository:
    @staticmethod
    def log_request(endpoint: str, method: str, attack_type: str, blocked: bool, ip: str) -> None:
        """
        Inserts a record into logs_security for every analyzed request.
        attack_type is stored as NULL when the request is clean (empty string).
        Uses a parameterized query to prevent SQL injection.
        """
        sql = """
            INSERT INTO logs_security (endpoint, method, attack_type, blocked, ip)
            VALUES (%s, %s, NULLIF(%s, ''), %s, %s)
        """
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (endpoint, method, attack_type, blocked, ip))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def update_and_check_rate_limit(endpoint: str, ip: str) -> bool:
        """
        Upserts a row in limit_rate for the given IP + endpoint combination.
        - First request from this IP+endpoint: inserts with count=1, blocked=FALSE.
        - Subsequent requests within the window: increments count, sets blocked=TRUE if over limit.
        - If the window has expired: resets count to 1 and unblocks.
        Returns True if the IP is currently blocked, False otherwise.
        Uses a parameterized query to prevent SQL injection.

        The window and threshold come from Config rather than being passed in
        by the caller: they're a single system-wide policy read from .env, not
        something an individual call site should be able to vary.
        """
        window_secs = Config.RATE_LIMIT_WINDOW_SECS
        max_requests = Config.RATE_LIMIT_MAX_REQUESTS

        sql = """
            INSERT INTO limit_rate (endpoint, ip, request_count, window_start, blocked_status)
            VALUES (%s, %s, 1, NOW(), FALSE)
            ON CONFLICT (ip, endpoint) DO UPDATE SET
                request_count = CASE
                    WHEN NOW() - limit_rate.window_start > make_interval(secs => %s) THEN 1
                    ELSE limit_rate.request_count + 1
                END,
                window_start = CASE
                    WHEN NOW() - limit_rate.window_start > make_interval(secs => %s) THEN NOW()
                    ELSE limit_rate.window_start
                END,
                blocked_status = CASE
                    WHEN NOW() - limit_rate.window_start > make_interval(secs => %s) THEN FALSE
                    WHEN limit_rate.request_count + 1 > %s THEN TRUE
                    ELSE limit_rate.blocked_status
                END
            RETURNING blocked_status
        """
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (endpoint, ip, window_secs, window_secs, window_secs, max_requests))
                row = cur.fetchone()
            conn.commit()
            return bool(row["blocked_status"]) if row else False
        finally:
            conn.close()