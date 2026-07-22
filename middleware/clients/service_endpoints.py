"""
The internal Docker-network addresses of the other three services.

These work because Docker Compose's internal DNS resolves each service name
(e.g. "users") to that container's address. Note the port is always 8080 -
each container's own listening port - never the distinct host-side ports
(8081/8082/8083) from docker-compose.yml's "ports:" mapping. Those only
apply to traffic arriving from outside Docker, e.g. Postman on the Windows
host; container-to-container traffic reaches the listening port directly.

Not read from .env on purpose: these are structural facts about how the
services are wired together in docker-compose.yml, not secrets or
per-environment settings - unlike DB credentials, they don't change between
people's machines.
"""

USERS = "http://users:8080"
SECURITY_ENGINE = "http://security_engine:8080"
BACKEND_REGISTRY = "http://backend_registry:8080"

# Every call this middleware makes to another internal service uses this
# timeout, in seconds. requests has NO default timeout - without an explicit
# one, a single hung service or slow real backend would tie up the request
# indefinitely instead of failing fast with a 500.
INTERNAL_CALL_TIMEOUT_SECS = 5