from flask import Blueprint, request, jsonify
from services.security_engine.services.security_service import SecurityService

analyze_bp = Blueprint("analyze", __name__)


@analyze_bp.post("/analyze")
def analyze():
    """
    Contract A: takes a request description from the middleware and returns
    whether it should be allowed, plus the attack type and reason.
    """
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "Invalid JSON body"}), 400

    if not all(k in payload for k in ("endpoint", "method", "ip")):
        return jsonify({"error": "Missing required fields: endpoint, method, ip"}), 400

    result = SecurityService.analyze_request(payload)

    # A clean request is a successful "checked, nothing found" outcome - 200.
    # A blocked request is reflected in the transport status too, not only in
    # the JSON body: 429 for rate_limit (a client can legitimately retry once
    # the window rolls over), 403 for sqli/xss (the request itself is
    # rejected). This mirrors _blocked_response in the middleware's
    # proxy_service, so a blocked verdict looks the same whether this endpoint
    # is called directly or reached through the proxy.
    status = 200
    if not result.get("allowed"):
        status = 429 if result.get("attack_type") == "rate_limit" else 403

    return jsonify(result), status