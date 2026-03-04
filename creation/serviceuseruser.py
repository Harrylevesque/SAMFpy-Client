import sys
import base64
import requests
import quantcrypt.kem as qkem
import quantcrypt.internal.pqa.kem_algos as algos
from kyber_py.ml_kem import ML_KEM_1024


from main import serviceip
from login.keypair import generate_client_keys as generate_signing_keys
from login.otp import generate_client_keys as generate_otp_keys


try:
    # Example: if your discover is MLKEM_768.keygen()
    kp = algos.MLKEM_768()
    pubkey, privkey = kp.keygen()


    KPek, KPdk = ML_KEM_1024.keygen()

    # Generate client signing keypair (raw bytes) for registration payload.
    client_pubkey, client_privkey = generate_signing_keys()

    # Generate OTP signing keypair: send pubkey to server, keep private key local.
    otp_privK, otp_pubK = generate_otp_keys()

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


# Ensure client signing pubkey is bytes for consistent transport encoding.
client_pub_bytes = to_bytes(client_pubkey)

# Ensure OTP keys are in bytes/strings expected by payload/file storage.

data = {
    "pubk": base64.b64encode(pub_bytes).decode(),
    "KPek": base64.b64encode(KPek).decode(),  # Key must be 'KPek' to match server
    "KPdk": base64.b64encode(KPdk).decode(),
    # Send exactly one base64 layer for client signing public key bytes.
    "client_pubk": base64.b64encode(client_pub_bytes).decode(),
    "otp_pubK": otp_pubK,
}
print("Request payload:", data)  # Debug print to verify outgoing keys
resp = requests.post(f"{serviceip}/service/{serviceuuid}/user/new", json=data)
print(resp.status_code)
try:
    print(resp.json())
except ValueError:
    print(resp.text)


def get_svu_creation_result():
    """Expose response data needed by saving.userfiles without circular imports.

    This now returns four values:
      - resp: the requests.Response from the server
      - serviceuuid: the service UUID used in the request
      - otp_privK: the OTP private key (kept locally)
      - client_privkey: the client signing private key (raw bytes)

    Callers should base64-encode client_privkey when persisting to JSON if it's bytes.
    """
    # Persist only OTP private key locally; OTP public key is sent to server in payload.
    return resp, serviceuuid, otp_privK, client_privkey


if __name__ == "__main__":
    # When run directly, just execute the request/prints. Saving is triggered from saving.userfiles.
    pass
