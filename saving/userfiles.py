# python
import os
import json
import ast
from typing import Optional
import base64
import requests
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

serviceip = os.getenv("host")

# generate_client_keys is intentionally not imported here to avoid circular imports.
# The creation module (creation/serviceuseruser.py) sends otp_pubK during registration
# and returns otp_privK from get_svu_creation_result(), which this module persists.

# Determine project root relative to this file and create storage/userfiles there
BASE_DIR = Path(__file__).resolve().parents[1]
storage_dir = BASE_DIR / "storage" / "userfiles"
storage_dir.mkdir(parents=True, exist_ok=True)
save_location = str(storage_dir)

serviceip = os.getenv("host")


def _ensure_scheme(url: str) -> str:
    if not url.startswith("http://") and not url.startswith("https://"):
        return "https://" + url
    return url


def update_humans_json(svc_ip: str, service_uuid: str, svu_uuid: Optional[str], username: Optional[str] = None) -> None:
    """GET {svc_ip}/humans, parse the response, and upsert into BASE_DIR/humans.json.

    Expected response shape (either form is accepted):
      {"human_readable_name": "...", "service_ip": "...", "contact_email": "...", "description": "..."}
    or wrapped:
      {"humans": "{'human_readable_name': ..., ...}"}
    """
    if not svc_ip or not service_uuid:
        return

    url = f"{_ensure_scheme(svc_ip).rstrip('/')}/humans"
    raw = {}
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            try:
                raw = resp.json()
            except Exception:
                try:
                    raw = ast.literal_eval(resp.text)
                except Exception:
                    raw = {}
        else:
            print(f"Warning: {url} returned {resp.status_code}")
    except Exception as e:
        print(f"Warning: could not fetch {url}: {e}")

    # Unwrap if server returns {"humans": "{'key': 'val'}"}
    humans_field = raw.get("humans", raw)
    if isinstance(humans_field, str):
        try:
            humans_field = json.loads(humans_field)
        except Exception:
            try:
                humans_field = ast.literal_eval(humans_field)
            except Exception:
                humans_field = {}

    hrn         = humans_field.get("human_readable_name", "")
    serviceip_v = humans_field.get("service_ip", "")
    contact     = humans_field.get("contact_email", "")
    description = humans_field.get("description", "")

    humans_file = BASE_DIR / "humans.json"
    humans = {}
    if humans_file.exists():
        try:
            with open(humans_file, "r") as f:
                humans = json.load(f)
        except Exception:
            humans = {}

    svc_entry = humans.get(service_uuid, {})
    svc_entry.update({
        "sv_uuid":       service_uuid,
        "hrn":           hrn,
        "serviceip":     serviceip_v,
        "contact_email": contact,
        "description":   description,
    })

    if svu_uuid:
        chosen_username = username or f"CHANGEME"
        svc_entry[svu_uuid] = {
            "svu_uuid": svu_uuid,
            "username": chosen_username,
        }

    humans[service_uuid] = svc_entry

    tmp = str(humans_file) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(humans, f, indent=2)
    os.replace(tmp, humans_file)


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


def save_response_svu(filename: Optional[str] = None, field: Optional[str] = None, serviceip_param: Optional[str] = None, service_uuid_param: Optional[str] = None) -> None:
    # Import lazily to avoid circular import at module load time
    from creation.serviceuseruser import get_svu_creation_result

    # Use provided parameters if given; fall back to environment-level serviceip
    svc_ip = serviceip_param or serviceip
    svc_uuid = service_uuid_param

    # Call the creation routine with explicit server IP and UUID
    resp, serviceuuid, otp_privK, client_privkey = get_svu_creation_result(serviceip=svc_ip, serviceuuid=svc_uuid)

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

    if svuUUID is None:
        raise Exception("No svuUUID")


    import webbrowser

    # Only open the registration URL if we have an explicit service IP
    if svc_ip:
        url = f"{svc_ip}?mode=register&sv-uuid={service_uuid}&svu-uuid={svuUUID}"
        try:
            webbrowser.open(url)
        except Exception:
            # Non-fatal if browser can't be opened in some environments
            pass

    # Fetch {serviceip}/humans and append to humans.json
    try:
        update_humans_json(svc_ip, service_uuid, svuUUID)
    except Exception as e:
        print(f"Warning: could not update humans.json: {e}")

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
