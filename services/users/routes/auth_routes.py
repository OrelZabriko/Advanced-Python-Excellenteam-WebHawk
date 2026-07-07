from flask import Blueprint, request, jsonify
from services.users.service import auth_service
from services.shared.exceptions import ServiceError

auth_bp = Blueprint("auth", __name__)


def _get_bearer_token():
    """
    Extracts the token from an 'Authorization: Bearer <token>' header.
    Returns None if the header is missing or malformed.
    """
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    return header.split(" ", 1)[1].strip()


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    try:
        user = auth_service.register_user(data.get("email"), data.get("password"))
        return jsonify({"id": user["id"], "email": user["email"]}), 201
    except ServiceError as e:
        return jsonify({"error": e.message}), e.status_code


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    try:
        token, expires_at = auth_service.login_user(
            data.get("email"), data.get("password"), request.remote_addr
        )
        return jsonify({"token": token, "expires_at": expires_at.isoformat()}), 200
    except ServiceError as e:
        return jsonify({"error": e.message}), e.status_code


@auth_bp.post("/logout")
def logout():
    token = _get_bearer_token()
    if not token:
        return jsonify({"error": "missing bearer token"}), 401
    try:
        auth_service.logout_user(token)
        return jsonify({"message": "logged out"}), 200
    except ServiceError as e:
        return jsonify({"error": e.message}), e.status_code


@auth_bp.get("/validate")
def validate():
    token = _get_bearer_token()
    if not token:
        return jsonify({"valid": False, "error": "missing bearer token"}), 401
    try:
        payload = auth_service.validate_token(token)
        return jsonify({
            "valid": True,
            "user_id": payload["user_id"],
            "email": payload["email"],
        }), 200
    except ServiceError as e:
        return jsonify({"valid": False, "error": e.message}), e.status_code