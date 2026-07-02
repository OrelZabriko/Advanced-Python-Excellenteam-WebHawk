import psycopg2
from psycopg2.extras import RealDictCursor
from services.shared.config import Config


def get_connection():
    """
    Returns a new PostgreSQL connection.
    Each repository call opens/closes its own connection+cursor
    to keep things simple and avoid shared-state bugs.
    """
    return psycopg2.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        dbname=Config.DB_NAME,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        cursor_factory=RealDictCursor,
    )