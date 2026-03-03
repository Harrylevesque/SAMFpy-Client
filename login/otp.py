import time
import secrets
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization

# === CONFIGURABLE PARAMETERS ===
INTERVAL = 5      # seconds per time bucket
TOLERANCE = 2     # bucket tolerance


def time_bucket(interval=INTERVAL):
    """Return the current time bucket."""
    return int(time.time()) // interval


def client_generate_single_use_otp():
    """
    Generates a single-use OTP using a fresh public/private keypair.

    Returns:
        nonce (str): crypto-random 128-bit nonce
        pk_bytes (bytes): public key bytes to send to server
        signature (bytes): signature of message
    """
    bucket = time_bucket()
    nonce = secrets.token_hex(16)  # 128-bit random nonce
    sk = ed25519.Ed25519PrivateKey.generate()
    pk = sk.public_key()

    # Message is bucket + nonce
    msg = f"{bucket}:{nonce}".encode()

    # Sign message
    signature = sk.sign(msg)

    # Convert public key to bytes for transmission
    pk_bytes = pk.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )

    return nonce, pk_bytes, signature



if __name__ == "__main__":
    nonce, pk_bytes, signature = client_generate_single_use_otp()
    print("Send to server:")
    print("Nonce:", nonce)
    print("Public Key:", pk_bytes.hex())
    print("Signature:", signature.hex())
