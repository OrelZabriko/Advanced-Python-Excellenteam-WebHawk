import logging
import requests
from flask import Request, Response, jsonify
from middleware.clients import service_endpoints
from middleware.utils.request_payload_builder import build_analyze_payload

logger = logging.getLogger(__name__)

# Headers that describe how *this* connection was encoded or framed, rather
# than the content itself. Passing them straight through from the real
# backend's response would make the client try to decode a body that has
# already been decoded by requests, or trust a length that no longer matches.
_HOP_BY_HOP_HEADERS = {
    "content-encoding",
    "content-length",
    "transfer-encoding",
    "connection",
    "keep-alive",
}


def blocked_response(attack_type):
    """
    Contract C's blocked-response shape - deliberately generic. It carries
    attack_type but never `reason`: returning the reason would tell an
    attacker exactly which detection rule fired, letting them fingerprint the
    rules and tune a payload around them.
    """
    status = 429 if attack_type == "rate_limit" else 403
    return jsonify({"error": "Request blocked", "attack_type": attack_type}), status


def _internal_error(context: str):
    """
    Shared "something went wrong talking to another service" handler, used by
    all four places this file makes an internal HTTP call (backend_registry's
    lookup, users' /validate, security_engine's /analyze, and the real backend
    itself).

    `context` is logged server-side only and never sent to the client. Putting
    it in the response body would mean anyone who triggers a 500 learns the
    internal service names that make up this system - useful to an attacker
    mapping the architecture, never needed by a legitimate client. The client
    always gets the same generic message regardless of which call failed.
    """
    logger.error("Internal error: %s", context)
    return jsonify({"error": "Internal server error"}), 500


def forward_to_real_backend(req: Request, target_url: str):
    """
    Step 4, the final step on the "allowed" path: forward the request to the
    registered backend and pass its response back to the client as-is.
    """
    url = target_url.rstrip("/") + req.path

    # Only a minimal, explicit set of headers is forwarded. Blindly copying
    # every incoming header (Host, Content-Length, etc.) is a common source of
    # subtle proxy bugs, so this is a deliberate simplification, not an
    # oversight. Extend this list if a registered backend needs to see more of
    # the original request.
    headers = {}
    if req.headers.get("Authorization"):
        headers["Authorization"] = req.headers["Authorization"]
    if req.headers.get("Content-Type"):
        headers["Content-Type"] = req.headers["Content-Type"]

    try:
        backend_response = requests.request(
            method=req.method,
            url=url,
            headers=headers,
            params=req.args,
            data=req.get_data(),
            timeout=service_endpoints.INTERNAL_CALL_TIMEOUT_SECS,
            # The middleware returns the backend's own response, including a
            # redirect, rather than quietly following it somewhere the caller
            # never asked to go and that was never security-checked.
            allow_redirects=False,
        )
    except requests.RequestException as e:
        return _internal_error(f"real backend unreachable or timed out: {e}")

    passthrough_headers = [
        (name, value)
        for name, value in backend_response.headers.items()
        if name.lower() not in _HOP_BY_HOP_HEADERS
    ]
    return Response(
        backend_response.content,
        status=backend_response.status_code,
        headers=passthrough_headers,
    )


def call_analyze(req: Request, target_url: str):
    """Step 3: ask security_engine whether this request is safe (Contract A)."""
    payload = build_analyze_payload(req)

    try:
        response = requests.post(
            f"{service_endpoints.SECURITY_ENGINE}/analyze",
            json=payload,
            timeout=service_endpoints.INTERNAL_CALL_TIMEOUT_SECS,
        )
        result = response.json()
    except requests.RequestException as e:
        return _internal_error(f"security_engine unreachable or timed out: {e}")
    except ValueError:
        return _internal_error("security_engine returned a non-JSON response")

    if not result.get("allowed"):
        # .get() rather than ["attack_type"]: Contract A says the key is
        # always present (as null on a clean request), but the middleware
        # shouldn't crash with a KeyError if that ever regresses - it should
        # still block the request, just without naming the attack type.
        return blocked_response(result.get("attack_type"))

    return forward_to_real_backend(req, target_url)


def validate_jwt(req: Request, target_url: str):
    """
    Step 2: validate the caller's JWT by calling the users service's own
    /validate endpoint, rather than decoding it here - so JWT_SECRET only ever
    needs to live in one service, not two.

    A valid Authorization header is REQUIRED on every request, with no
    exceptions. Skipping this check when the header is missing would let
    anyone bypass authentication entirely just by omitting it - the exact
    thing the check exists to prevent. If a registered backend ever needs a
    genuinely public endpoint, that should be a deliberate opt-in on the
    registration, not implied by what the caller happened to send.
    """
    auth_header = req.headers.get("Authorization")
    if not auth_header:
        return jsonify({"error": "Authorization header required"}), 401

    try:
        response = requests.get(
            f"{service_endpoints.USERS}/validate",
            headers={"Authorization": auth_header},
            timeout=service_endpoints.INTERNAL_CALL_TIMEOUT_SECS,
        )
    except requests.RequestException as e:
        return _internal_error(f"users service unreachable or timed out: {e}")

    # A 5xx from users means the check couldn't be performed at all - which is
    # different from the check running and rejecting the token. Treating it as
    # "invalid token" would return a misleading 401 and hide a real outage.
    if response.status_code >= 500:
        return _internal_error("users service returned an internal error")

    try:
        result = response.json()
    except ValueError:
        return _internal_error("users service returned a non-JSON response")

    if not result.get("valid"):
        return jsonify({"error": "Invalid or expired token"}), 401

    return call_analyze(req, target_url)


def handle_request(req: Request):
    """
    The core of WebHawk - this runs for every single incoming request (see
    proxy_routes.py's catch-all; there are no other routes in this service).

    Flow:
      1. Read the caller's API key and resolve it via backend_registry
         (Contract B).
      2. Validate the JWT via the users service's /validate endpoint.
      3. Send the request to security_engine's /analyze (Contract A).
      4. If blocked -> return Contract C's blocked response directly, without
         ever contacting the real backend.
         If allowed -> forward to the registered target_url and pass the real
         backend's response back to the client as-is.
    """
    # Contract B defines the lookup (given a key, find the target) but not how
    # the key travels on the request; the X-API-Key header is this project's
    # chosen convention.
    api_key = req.headers.get("X-API-Key")
    if not api_key:
        return jsonify({"error": "Missing X-API-Key header"}), 401

    try:
        response = requests.get(
            f"{service_endpoints.BACKEND_REGISTRY}/backends/lookup",
            # params= rather than building the query string by hand, so the
            # key is URL-encoded correctly.
            params={"api_key": api_key},
            timeout=service_endpoints.INTERNAL_CALL_TIMEOUT_SECS,
        )
        result = response.json()
    except requests.RequestException as e:
        return _internal_error(f"backend_registry unreachable or timed out: {e}")
    except ValueError:
        return _internal_error("backend_registry returned a non-JSON response")

    if not result.get("found"):
        return jsonify({"error": "Unknown API key"}), 404

    # Checked before contacting security_engine at all: if protection is
    # paused there is no target to forward to, so analyzing the request would
    # be wasted work and would log a security event for traffic that was never
    # going to be proxied.
    if not result.get("active"):
        return jsonify({"error": "This backend's protection is currently paused"}), 403

    return validate_jwt(req, result["target_url"])