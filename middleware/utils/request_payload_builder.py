from flask import Request


def build_analyze_payload(req: Request) -> dict:
    """
    Converts an incoming client request into the JSON shape Contract A
    defines for POST /analyze: endpoint, method, ip, headers, query_params,
    path_params, body.
    """
    body = _extract_body_for_scanning(req)

    return {
        "endpoint": req.path,
        "method": req.method,
        "ip": req.remote_addr,
        "headers": dict(req.headers),
        "query_params": req.args.to_dict(),
        # This middleware is registered as a single catch-all route (see
        # proxy_routes.py), not a set of routes with named placeholders like
        # "/users/<id>" - so there is no route pattern to extract named path
        # params from. Always empty. security_engine's analyzer doesn't use
        # path_params for anything today, so this hasn't mattered in practice.
        "path_params": {},
        "body": body,
    }


def _extract_body_for_scanning(req: Request) -> dict:
    """
    Best-effort extraction of scannable fields from the request body, for
    security_engine's attack-pattern detection - NOT what actually gets
    forwarded to the real backend (see proxy_service._forward_to_real_backend,
    which sends the original raw bytes regardless of what happens here).

    Tries JSON first, then form-encoded fields (application/x-www-form-urlencoded
    or multipart/form-data) - a SQLi/XSS payload sitting in an ordinary HTML
    form field is just as real an attack as one in a JSON field, and skipping
    it here would mean it's never scanned at all. Only falls back to an empty
    dict when the body is genuinely neither (e.g. a file upload's binary
    content, or no body at all) - there's nothing text-based to scan there.
    """
    json_body = req.get_json(silent=True)
    if isinstance(json_body, dict):
        return json_body

    if req.form:
        return req.form.to_dict()

    return {}