import logging
from flask import jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    """
    Makes every error this app returns a JSON response, so a client parsing
    JSON never receives Flask's default HTML error page instead.

    Without this, an unhandled exception (a dropped database connection being
    the realistic one) returns an HTML page with a 500 - and any client that
    calls response.json() on it crashes on a parse error, reporting something
    unrelated to the actual problem.

    Imports nothing from config.py on purpose: that keeps this usable from the
    middleware, which has no database and no environment variables, and which
    would otherwise be forced to load - and fail - Config's DB_PASSWORD check.
    """

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        # Flask's own 404/405/400 responses arrive here. The status code and
        # message are already correct - they just need to be JSON rather than
        # HTML, so a 404 from a typo'd URL has the same response shape as
        # every deliberate error the services return themselves.
        return jsonify({"error": e.description}), e.code

    @app.errorhandler(Exception)
    def handle_unexpected_exception(e):
        # Anything not already an HTTPException is a bug or an outage, not a
        # handled case. The full traceback goes to the server log via
        # exception(); the client gets a fixed, generic message.
        #
        # The exception text is deliberately not included in the response:
        # psycopg2 errors in particular embed the database host, port, and
        # user, which would hand an attacker real infrastructure details from
        # a single failed request.
        logger.exception("Unhandled exception: %s", e)
        return jsonify({"error": "Internal server error"}), 500