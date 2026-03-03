from nacl.signing import SigningKey
from nacl.encoding import Base64Encoder

def generate_client_keys():
    signing_key = SigningKey.generate()
    private_key = signing_key.encode()
    public_key = signing_key.verify_key.encode()
    return public_key, private_key


def export_public_key(public_key: bytes) -> str:
    return Base64Encoder.encode(public_key).decode()




def sign_challenge(private_key: bytes, challenge: bytes) -> bytes:
    signing_key = SigningKey(private_key)
    signed = signing_key.sign(challenge)
    return signed

if __name__ == '__main__':
    generate_client_keys()