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



def sign_challenge_otp(private_key: bytes, payload_json) -> bytes:
    """Sign an OTP challenge.

    Accepts payload_json as either str or bytes (UTF-8). Returns the signed message bytes.
    Raises ValueError with clear messages on bad input.
    """
    # Ensure payload_json is a str containing JSON
    if isinstance(payload_json, bytes):
        try:
            payload_text = payload_json.decode('utf-8')
        except UnicodeDecodeError:
            # fallback to surrogatepass to preserve bytes if necessary
            payload_text = payload_json.decode('utf-8', errors='surrogatepass')
    elif isinstance(payload_json, str):
        payload_text = payload_json
    else:
        raise ValueError("payload_json must be str or bytes containing JSON")

    try:
        payload = json.loads(payload_text)
    except Exception as e:
        raise ValueError(f"Failed to parse payload_json as JSON: {e}")

    if 'challenge' not in payload or 'issued_at' not in payload:
        raise ValueError("payload_json must contain 'challenge' and 'issued_at' fields")

    # challenge is base64 encoded in the JSON
    try:
        challenge = Base64Encoder.decode(payload["challenge"].encode())
    except Exception as e:
        raise ValueError(f"Failed to decode 'challenge' from base64: {e}")

    issued_at = payload["issued_at"]

    signing_key = SigningKey(private_key)
    message = challenge + str(issued_at).encode()

    signed = signing_key.sign(message)



    return signed


# Backwards-compatible alias
sign_challenge = sign_challenge_otp

