import sys
import base64
import requests
import quantcrypt.kem as qkem
import quantcrypt.internal.pqa.kem_algos as algos

from main import serviceip

try:
    # Example: if your discover is MLKEM_768.keygen()
    kp = algos.MLKEM_768()
    pubkey, privkey = kp.keygen()
except Exception as e:
    print(f"quantcrypt imported but could not generate keypair: {e}")
    sys.exit(1)


def to_bytes(x):
    if isinstance(x, (bytes, bytearray, memoryview)):
        return bytes(x)
    if isinstance(x, str):
        return x.encode()
    raise TypeError("unexpected key type")


try:
    pub_bytes = to_bytes(pubkey)
    priv_bytes = to_bytes(privkey)
except TypeError as e:
    print(f"Unexpected key types: {e}")
    sys.exit(1)


print(f"Private key length: {len(priv_bytes)} bytes")
print(f"Public key length: {len(pub_bytes)} bytes")

data = {"pubk": base64.b64encode(pub_bytes).decode()}
resp = requests.post(f"{serviceip}/serviceuser/new", json=data)
print(resp.status_code)
try:
    print(resp.json())
except ValueError:
    print(resp.text)


def get_user_creation_result():
    """Expose resp and privkey for saving.userfiles without importing it here."""
    return resp, privkey


if __name__ == "__main__":
    # When run directly, just execute the request and print; saving is handled from saving.userfiles.
    pass

