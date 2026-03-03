from nacl.signing import SigningKey
from nacl.encoding import Base64Encoder


# -----------------------------
# Generate keypair
# -----------------------------
def generate_client_keys():
    signing_key = SigningKey.generate()
    private_key = signing_key.encode()
    public_key = signing_key.verify_key.encode()
    return public_key, private_key


# -----------------------------
# Export public key safely for transport
# (Base64 so it can go over JSON / HTTP / sockets)
# -----------------------------
def export_public_key(public_key: bytes) -> str:
    return Base64Encoder.encode(public_key).decode()


# -----------------------------
# Sign server challenge
# -----------------------------
def sign_challenge(private_key: bytes, challenge: bytes) -> bytes:
    signing_key = SigningKey(private_key)
    signed = signing_key.sign(challenge)
    return signed  # signature + message

if __name__ == '__main__':
    generate_client_keys()