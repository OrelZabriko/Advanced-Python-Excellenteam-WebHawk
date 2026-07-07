import bcrypt
from services.users.utils.constants import ENCODING

def hash_password(plain_password: str) -> str:
    hashed = bcrypt.hashpw(plain_password.encode(ENCODING), bcrypt.gensalt())
    return hashed.decode(ENCODING)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode(ENCODING),
        password_hash.encode(ENCODING),
    )