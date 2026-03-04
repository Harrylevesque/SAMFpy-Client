from nacl.signing import SigningKey
from nacl.encoding import Base64Encoder
import json


def generate_client_keys():
    signing_key = SigningKey.generate()
    private_key = signing_key.encode()
    public_key = signing_key.verify_key.encode()

    def export_public_key(public_key: bytes) -> str:
        return Base64Encoder.encode(public_key).decode()


    otp_privK = export_public_key(private_key)
    otp_pubK = export_public_key(public_key)
    return otp_privK, otp_pubK



def sign_challenge(private_key: bytes, payload_json: str) -> bytes:
    signing_key = SigningKey(private_key)

    payload = json.loads(payload_json)

    challenge = Base64Encoder.decode(payload["challenge"].encode())
    issued_at = payload["issued_at"]

    message = challenge + str(issued_at).encode()

    signed = signing_key.sign(message)
    return signed

