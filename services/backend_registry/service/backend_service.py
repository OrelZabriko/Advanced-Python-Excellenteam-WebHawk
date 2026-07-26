from services.backend_registry.repository import backend_repository
from services.backend_registry.utils.api_key_generator import generate_api_key
from services.shared.exceptions import ServiceError


def register_backend(service_name: str, target_url: str):
    """
    Registers a new backend and issues it a fresh API key.

    Raises ServiceError(400) if input is missing or target_url isn't a URL.
    Returns the created row, api_key included - the caller must store it
    now, since no endpoint ever returns it again after this.

    A collision on the generated api_key is astronomically unlikely (128
    bits of randomness) - not handled as a special case here, the same way
    the rest of this codebase currently accepts that class of race
    condition rather than adding exception-specific handling for it.
    """
    if not service_name or not target_url:
        raise ServiceError("service_name and target_url are required", 400)

    if not (target_url.startswith("http://") or target_url.startswith("https://")):
        raise ServiceError("target_url must start with http:// or https://", 400)

    api_key = generate_api_key()
    return backend_repository.create_backend(service_name, target_url, api_key)


def lookup_by_api_key(api_key: str):
    """
    Contract B: resolves an API key to where a request should be forwarded.

    Returns the backend row, or None if not found. "Not found" is a normal,
    expected outcome for this lookup (see Contract B's { "found": false }
    response), not an error condition.
    """
    return backend_repository.get_backend_by_api_key(api_key)


def list_all_backends():
    """
    Lists every registered backend. api_key is never included in the
    result - see backend_repository.get_all_backends for why.
    """
    return backend_repository.get_all_backends()


def update_backend(backend_id: int, service_name: str, target_url: str):
    """
    Updates a registration's service_name/target_url.

    Raises ServiceError(400) on missing/invalid input, (404) if no
    registration with this id exists.
    """
    if not service_name or not target_url:
        raise ServiceError("service_name and target_url are required", 400)

    if not (target_url.startswith("http://") or target_url.startswith("https://")):
        raise ServiceError("target_url must start with http:// or https://", 400)

    updated = backend_repository.update_backend(backend_id, service_name, target_url)
    if not updated:
        raise ServiceError("backend registration not found", 404)


def set_active_status(backend_id: int, active: bool):
    """
    Pauses or resumes protection for a registration without deleting it.

    Raises ServiceError(404) if no registration with this id exists.
    """
    updated = backend_repository.update_active_status(backend_id, active)
    if not updated:
        raise ServiceError("backend registration not found", 404)