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
    return jsonify(result), 200