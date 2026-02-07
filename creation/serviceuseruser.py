import sys
import base64
import requests
import quantcrypt.kem as qkem
import quantcrypt.internal.pqa.kem_algos as algos
from kyber_py.ml_kem import ML_KEM_1024


from main import serviceip


try:
    # Example: if your discover is MLKEM_768.keygen()
    kp = algos.MLKEM_768()
    pubkey, privkey = kp.keygen()


    KPek, KPdk = ML_KEM_1024.keygen()

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

serviceuuid = input("Enter service UUID: ")


data = {
    "pubk": base64.b64encode(pub_bytes).decode(),
    "KPek": base64.b64encode(KPek).decode(),  # Key must be 'KPek' to match server
    "KPdk": base64.b64encode(KPdk).decode()
}
print("Request payload:", data)  # Debug print to verify outgoing keys
resp = requests.post(f"{serviceip}/service/{serviceuuid}/user/new", json=data)
print(resp.status_code)
try:
    print(resp.json())
except ValueError:
    print(resp.text)


def get_svu_creation_result():
    """Helper to expose resp, serviceuuid and privkey without importing saving.userfiles.

    This is used by saving.userfiles.save_response_svu to avoid a circular import.
    """
    return resp, serviceuuid, privkey, KPdk, KPek


if __name__ == "__main__":
    # When run directly, just execute the request/prints. Saving is triggered from saving.userfiles.
    pass
