# python
import os
import json
from typing import Optional
import base64
import requests
from pathlib import Path

# generate_client_keys is intentionally not imported here to avoid circular imports.
# The creation module (creation/serviceuseruser.py) sends otp_pubK during registration
# and returns otp_privK from get_svu_creation_result(), which this module persists.

# Determine project root relative to this file and create storage/userfiles there
BASE_DIR = Path(__file__).resolve().parents[1]
storage_dir = BASE_DIR / "storage" / "userfiles"
storage_dir.mkdir(parents=True, exist_ok=True)
save_location = str(storage_dir)


def save_response_u(filename: Optional[str] = None, field: Optional[str] = None) -> None:
    from creation.serviceuser import get_user_creation_result

    resp, privkey = get_user_creation_result()

    try:
        data = resp.json()
    except ValueError:
        data = {"raw": resp.text, "status_code": resp.status_code}

    privkey_str = base64.b64encode(privkey).decode("ascii") if isinstance(privkey, (bytes, bytearray)) else str(privkey)
    data["privkey"] = privkey_str
    user_uuid = data.get("userUUID") or data.get("useruuid")

    if filename is None:
        filename = f"{save_location}/{user_uuid}.json" if user_uuid else os.path.join(save_location, "response.json")
        print(filename)
    else:
        dirpath = os.path.dirname(filename)
        if dirpath:
            os.makedirs(dirpath, exist_ok=True)

    with open(filename, "w") as f:
        if field:
            value = data.get(field)
            f.write(value if isinstance(value, str) else json.dumps(value))
        else:
            f.write(json.dumps(data, indent=2))

    print(privkey)


def save_response_sv(filename: Optional[str] = None, field: Optional[str] = None) -> None:
    # Import lazily to avoid circular import and to fetch the latest response
    from creation.service import get_service_creation_result

    resp, useruuid, privkey = get_service_creation_result()

    # Normalise useruuid: strip any trailing .json if user pasted it
    useruuid = useruuid.strip()
    if useruuid.endswith(".json"):
        useruuid = useruuid[:-5]

    # Try to parse JSON; if it fails (e.g. 500 HTML), fall back to using resp.text
    try:
        data = resp.json()
    except (ValueError, requests.exceptions.RequestException, Exception):
        data = {"raw": resp.text, "status_code": resp.status_code}

    privkey_str = base64.b64encode(privkey).decode("ascii") if isinstance(privkey, (bytes, bytearray)) else str(privkey)
    data["privkey"] = privkey_str

    service_uuid = data.get("serviceuuid") or data.get("serviceUUID")
    # Prefer the explicitly entered useruuid as the identifier
    user_uuid = useruuid or data.get("userUUID") or data.get("useruuid")

    # If the caller passes an explicit filename, just honour it like before
    if filename is not None:
        dirpath = os.path.dirname(filename)
        if dirpath:
            os.makedirs(dirpath, exist_ok=True)

        with open(filename, "w") as f:
            if field:
                value = data.get(field)
                f.write(value if isinstance(value, str) else json.dumps(value))
            else:
                f.write(json.dumps(data, indent=2))

        print(privkey)
        return

    # No explicit filename: follow the desired behaviour
    # 1) Create/overwrite a file with the user UUID as the name
    if user_uuid:
        base_user_file = os.path.join(save_location, f"{user_uuid}.json")
        with open(base_user_file, "w") as f:
            if field:
                value = data.get(field)
                f.write(value if isinstance(value, str) else json.dumps(value))
            else:
                f.write(json.dumps(data, indent=2))
    else:
        base_user_file = None

    # 2) Create a directory with that same UUID name (if we have one)
    #    and then write the service-specific file inside it.
    if service_uuid and user_uuid:
        dirpath = os.path.join(save_location, user_uuid)
        # If a file with this name already exists, remove it so a directory can be created
        if os.path.isfile(dirpath):
            os.remove(dirpath)
        os.makedirs(dirpath, exist_ok=True)
        filename = os.path.join(dirpath, f"{service_uuid}.json")
    elif service_uuid:
        # Fallback: just use the service UUID as a plain file name inside the storage dir
        filename = os.path.join(save_location, f"{service_uuid}.json")
    else:
        filename = os.path.join(save_location, "response.json")

    with open(filename, "w") as f:
        if field:
            value = data.get(field)
            f.write(value if isinstance(value, str) else json.dumps(value))
        else:
            f.write(json.dumps(data, indent=2))

    print(privkey)


def save_response_svu(filename: Optional[str] = None, field: Optional[str] = None) -> None:
    # Import lazily to avoid circular import at module load time
    from creation.serviceuseruser import get_svu_creation_result

    # get_svu_creation_result returns response, service UUID and locally-kept OTP private key.
    # Updated: get_svu_creation_result now also returns client_privkey for persistence
    resp, serviceuuid, otp_privK, client_privkey = get_svu_creation_result()

    try:
        data = resp.json()
    except ValueError:
        data = {"raw": resp.text, "status_code": resp.status_code}

    # Handle error response (list) gracefully
    if isinstance(data, list):
        print(f"Error from server: {data}")
        return

    # Persist only OTP private key locally; OTP public key is sent to server during registration.
    data["otp_privK"] = otp_privK
    # Persist client signing private key so login/processor can use it later.
    # Encode bytes as base64 string for safe JSON storage.
    if isinstance(client_privkey, (bytes, bytearray, memoryview)):
        data["client_privkey"] = base64.b64encode(bytes(client_privkey)).decode("ascii")
    else:
        data["client_privkey"] = str(client_privkey)

    service_uuid = data.get("serviceuuid") or data.get("serviceUUID") or serviceuuid
    svuUUID = data.get("svuUUID") or data.get("svuUuid") or data.get("svuuuid")

    if filename is None:
        if service_uuid:
            if svuUUID:
                dirpath = os.path.join(save_location, service_uuid)
                os.makedirs(dirpath, exist_ok=True)
                filename = os.path.join(dirpath, f"{svuUUID}.json")
            else:
                filename = os.path.join(save_location, "fail.json")
        else:
            filename = os.path.join(save_location, "fail.json")
    else:
        dirpath = os.path.dirname(filename)
        if dirpath:
            os.makedirs(dirpath, exist_ok=True)

    with open(filename, "w") as f:
        if field:
            value = data.get(field)
            f.write(value if isinstance(value, str) else json.dumps(value))
        else:
            f.write(json.dumps(data, indent=2))


def add_otp_pubK_to_svu_file(svu_uuid: str) -> bool:
    raise NotImplementedError("otp_pubK is now sent during registration and not added to local SVU files.")


if __name__ == "__main__":
    # Default to service-user variant when run directly
    save_response_sv()
