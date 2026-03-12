import sys
import base64
import requests
import quantcrypt.kem as qkem
import quantcrypt.internal.pqa.kem_algos as algos
from kyber_py.kyber import Kyber1024
from kyber_py.ml_kem import ML_KEM_1024
from quantcrypt import kem

from login.keypair import generate_client_keys as generate_signing_keys
from login.otp import generate_client_keys as generate_otp_keys


def to_bytes(x):
    if isinstance(x, (bytes, bytearray, memoryview)):
        return bytes(x)
    if isinstance(x, str):
        return x.encode()
    raise TypeError("unexpected key type")


def get_svu_creation_result(serviceip: str = None, serviceuuid: str = None):
    """Generate required keys, call the service registration endpoint, and
    return (resp, serviceuuid, otp_privK, client_privkey).

    If `serviceip` is None, attempt to import `serviceip` from main (environment
    fallback). If `serviceuuid` is None, fall back to an interactive prompt.
    """
    # Lazy import of main.serviceip as a fallback so callers (like the UI) can
    # supply their own values without triggering environment reads at import time.
    if serviceip is None:
        try:
            from main import serviceip as _svc
            serviceip = _svc
        except Exception:
            serviceip = None

    if serviceuuid is None:
        # Interactive fallback to preserve prior behavior for CLI usage
        serviceuuid = input("Enter service UUID: ")

    try:
        # Example: if your discover is MLKEM_768.keygen()
        kp = algos.Kyber768()
        pubkey, privkey = kp.keygen()

        KPek, KPdk = Kyber1024.keygen()

        # Generate client signing keypair (raw bytes) for registration payload.
        client_pubkey, client_privkey = generate_signing_keys()

        # Generate OTP signing keypair: send pubkey to server, keep private key local.
        otp_privK, otp_pubK = generate_otp_keys()

    except Exception as e:
        print(f"quantcrypt imported but could not generate keypair: {e}")
        raise

    try:
        pub_bytes = to_bytes(pubkey)
        priv_bytes = to_bytes(privkey)
    except TypeError as e:
        print(f"Unexpected key types: {e}")
        raise

    # Ensure client signing pubkey is bytes for consistent transport encoding.
    client_pub_bytes = to_bytes(client_pubkey)

    data = {
        "pubk": base64.b64encode(pub_bytes).decode(),
        "KPek": base64.b64encode(KPek).decode(),  # Key must be 'KPek' to match server
        "KPdk": base64.b64encode(KPdk).decode(),
        # Send exactly one base64 layer for client signing public key bytes.
        "client_pubk": base64.b64encode(client_pub_bytes).decode(),
        "otp_pubK": otp_pubK,
    }

    if not serviceip:
        raise RuntimeError("serviceip is required to contact the registration endpoint")
    if not serviceuuid:
        raise RuntimeError("serviceuuid is required to contact the registration endpoint")

    resp = requests.post(f"{serviceip}/service/{serviceuuid}/user/new", json=data)

    return resp, serviceuuid, otp_privK, client_privkey


if __name__ == "__main__":
    # When run directly, prompt for missing values and perform the request.
    try:
        resp, serviceuuid, otp_privK, client_privkey = get_svu_creation_result()
        try:
            print(resp.status_code)
            print(resp.json())
        except ValueError:
            print(resp.text)
    except Exception as e:
        print(f"Error during SVU creation: {e}")
