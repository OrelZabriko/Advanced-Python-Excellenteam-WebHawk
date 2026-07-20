import secrets


def generate_api_key() -> str:
    """
    Returns a new random API key of the form "whk_live_<32 hex characters>".

    Uses secrets.token_hex, which draws from the OS's cryptographically
    secure random source (os.urandom) - not Python's default `random`
    module, which is deterministic and unsuitable for anything security
    sensitive. 16 bytes = 32 hex characters = 128 bits of randomness.

    Not a password: this is a bearer credential a developer pastes into
    their own backend's config, but it's still generated with real
    randomness rather than anything guessable.
    """
    return f"whk_live_{secrets.token_hex(16)}"