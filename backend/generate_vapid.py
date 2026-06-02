"""
Run once to generate VAPID keys for Web Push.
    python generate_vapid.py
Copy the output into your .env file (and Render environment variables).
"""
import base64
from cryptography.hazmat.primitives.asymmetric.ec import generate_private_key, SECP256R1
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


if __name__ == '__main__':
    key = generate_private_key(SECP256R1())
    priv_bytes = key.private_numbers().private_value.to_bytes(32, 'big')
    pub_bytes = key.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)

    print("Add these to your backend/.env and Render environment variables:\n")
    print(f"VAPID_PRIVATE_KEY={b64url(priv_bytes)}")
    print(f"VAPID_PUBLIC_KEY={b64url(pub_bytes)}")
