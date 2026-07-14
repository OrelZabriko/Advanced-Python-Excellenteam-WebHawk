from services.users.utils.jwt_utils import generate_token, decode_token
from services.users.utils.constants import CLAIM_USER_ID, CLAIM_EMAIL

token, expires = generate_token(1, "test@example.com")
print("Token:", token)
print("Length:", len(token))

decoded = decode_token(token)
print("User ID:", decoded[CLAIM_USER_ID])
print("Email:", decoded[CLAIM_EMAIL])