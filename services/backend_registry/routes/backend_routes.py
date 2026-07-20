from flask import Blueprint, request, jsonify
from services.backend_registry.service import backend_service
from services.shared.exceptions import ServiceError

backend_bp = Blueprint("backend", __name__)


@backend_bp.post("/backends")
def register_backend():
    data = request.get_json(silent=True) or {}
    try:
        backend = backend_service.register_backend(
            data.get("service_name"), data.get("target_url")
        )
        return jsonify({
            "id": backend["id"],
            "service_name": backend["service_name"],
            "target_url": backend["target_url"],
            # Shown here once, at creation time - the caller must save this
            # now, the same way a real secret/API key is normally issued.
            "api_key": backend["api_key"],
            "active": backend["active"],
            "created_at": backend["created_at"].isoformat(),
        }), 201
    except ServiceError as e:
        return jsonify({"error": e.message}), e.status_code


@backend_bp.get("/backends/lookup")
def lookup_backend():
    api_key = request.args.get("api_key")
    if not api_key:
        return jsonify({"error": "missing required query parameter: api_key"}), 400

    backend = backend_service.lookup_by_api_key(api_key)

    # 200 either way - per Contract B, "not found" is a normal, expected
    # business outcome for this endpoint, not a transport error.
    if not backend:
        return jsonify({"found": False}), 200

    return jsonify({
        "found": True,
        "service_name": backend["service_name"],
        "target_url": backend["target_url"],
        "active": backend["active"],
    }), 200


@backend_bp.get("/backends")
def list_backends():
    backends = backend_service.list_all_backends()
    return jsonify({
        "backends": [
            {
                "id": b["id"],
                "service_name": b["service_name"],
                "target_url": b["target_url"],
                "active": b["active"],
                "created_at": b["created_at"].isoformat(),
            }
            for b in backends
        ]
    }), 200


@backend_bp.put("/backends/<int:backend_id>")
def update_backend(backend_id):
    """
    PUT /backends/<id> - updates a registration's service_name and target_url.

    Deliberately cannot change api_key or active:
      - api_key is issued once at creation and never rotated through this endpoint, so a typo in an
        update can't silently invalidate the key a developer already deployed to their own backend.
      - active has its own endpoint (PATCH /backends/<id>/status), since pausing protection is a
        different intent from correcting a URL.

    Request body (both fields required):
        { "service_name": "my-shop-api", "target_url": "https://..." }

    Responses:
        200 - updated
        400 - a field is missing, or target_url isn't http:// or https://
        404 - no registration with this id
    """
    # get_json() raises a 415/400 and aborts the request if the body isn't
    # valid JSON or the Content-Type header is missing. silent=True makes it
    # return None instead of raising, and the `or {}` turns that None into an
    # empty dict.
    #
    # The point is who gets to decide what the error looks like. Without
    # this, a request with no body would be rejected by Flask itself, with
    # Flask's own HTML error page - before any of this function's own
    # validation ever runs. With it, an empty body flows through as {},
    # data.get("service_name") returns None, and the service layer raises
    # ServiceError("service_name and target_url are required", 400) - a
    # clean JSON error, in the same shape as every other error this API returns.
    #
    # data.get(...) rather than data[...] for the same reason: a missing key
    # returns None instead of raising KeyError, so validation stays in the
    # service layer where every other rule lives, instead of being split
    # between an exception here and a check there.
    #
    # This matches the pattern already used in the users service's routes.
    data = request.get_json(silent=True) or {}
    try:
        backend_service.update_backend(
            backend_id, data.get("service_name"), data.get("target_url")
        )
        return jsonify({
            "id": backend_id,
            "service_name": data.get("service_name"),
            "target_url": data.get("target_url"),
            "message": "backend updated successfully",
        }), 200
    except ServiceError as e:
        return jsonify({"error": e.message}), e.status_code


@backend_bp.patch("/backends/<int:backend_id>/status")
def set_backend_status(backend_id):
    data = request.get_json(silent=True) or {}
    if "active" not in data:
        return jsonify({"error": "missing required field: active (boolean)"}), 400

    active = bool(data["active"])
    try:
        backend_service.set_active_status(backend_id, active)
        return jsonify({
            "id": backend_id,
            "active": active,
            "message": "status updated successfully",
        }), 200
    except ServiceError as e:
        return jsonify({"error": e.message}), e.status_code