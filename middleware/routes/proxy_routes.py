from flask import Blueprint, request
from middleware.services import proxy_service

proxy_bp = Blueprint("proxy", __name__)

# No individual routes are registered on purpose. This service is a single
# "front door" for every request a client sends - the project spec's "client
# sends a request to WebHawk instead of the real server". These two rules
# together catch every path: the first matches the bare root ("/"), the
# second matches everything below it, with <path:...> rather than <string:...>
# so that slashes inside the path are captured too (a plain <string:> stops
# at the first "/").
_ALL_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


@proxy_bp.route("/", defaults={"path": ""}, methods=_ALL_METHODS)
@proxy_bp.route("/<path:path>", methods=_ALL_METHODS)
def proxy(path):
    # `path` is captured only to satisfy the route pattern - the proxy reads
    # the full path off the request object itself, so it never needs to
    # reassemble it from this fragment.
    return proxy_service.handle_request(request)