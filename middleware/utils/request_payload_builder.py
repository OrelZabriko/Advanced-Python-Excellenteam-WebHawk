from flask import Request


def build_analyze_payload(req: Request) -> dict:
    """
    Converts an incoming client request into the JSON shape Contract A
    defines for POST /analyze: endpoint, method, ip, headers, query_params,
    path_params, body.
    """
    # A non-JSON or empty body becomes an empty dict rather than being
    # omitted, since security_engine's _collect_all_strings always expects a
    # (possibly empty) value at "body" and would otherwise skip it silently.
    body = req.get_json(silent=True)
    if not isinstance(body, dict):
        body = {}

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