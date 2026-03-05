from flask.cli import load_dotenv

from saving.workingfiles import save_workingfiles
from login.keymatch import keymatch
from login.keypair import sign_challenge_keypair
from saving.workingfiles import update_workingfile_status
from login.otp import sign_challenge_otp

from pathlib import Path
from typing import Optional
import json
import os
import requests
import base64

load_dotenv()
serviceip = os.getenv("host")

def keypair(sv_uuid, svu_uuid, con_uuid):
    serviceip = os.getenv("host")
    responce = requests.get(f"{serviceip}/login/{con_uuid}/step/3")
    resp_json = responce.json()
    print("Step 3 response:", resp_json)
    challenge_b64 = resp_json.get("challenge")
    if challenge_b64 is None:
        raise ValueError("No 'challenge' key found in response")
    try:
        challenge = base64.b64decode(challenge_b64)
    except Exception as e:
        raise ValueError(f"Failed to decode challenge from base64: {e}")
    save_location = os.getenv("BASE_SAVE_DIR", "./storage") + "/userfiles"
    target_file = Path(save_location) / sv_uuid / f"{svu_uuid}.json"

    # Check that the user file exists before trying to open it
    if not target_file.exists():
        print(f"User file not found: `{target_file.resolve()}`.")
        return None

    with open(target_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        privK = data.get("client_privkey")
        if privK is None:
            raise ValueError("No 'client_privkey' found in user file")
        try:
            privK_bytes = base64.b64decode(privK)
        except Exception as e:
            raise ValueError(f"Failed to decode client_privkey from base64: {e}")
        if len(privK_bytes) != 32:
            raise ValueError(f"Decoded client_privkey is {len(privK_bytes)} bytes, expected 32 bytes.")
    signature = sign_challenge_keypair(privK_bytes, challenge)
    data3_5 = {
        "signature": base64.b64encode(signature).decode("ascii"),
        "challenge": challenge_b64
    }
    keypairValid = requests.post(f"{serviceip}/login/{con_uuid}/step/3.5", data=json.dumps(data3_5))

    keypairValid_json = keypairValid.json()
    update_workingfile_status(
        con_uuid=con_uuid,
        status=keypairValid_json.get("status", "keypair_complete"),
        step_name="keypair",
        time_of_last_completion=keypairValid_json.get("time_of_last_completion"),
    )


    print(keypairValid.text)
    return keypairValid.content


def otp(con_uuid):
    # Fetch the server's OTP challenge (full response)
    step4response = requests.get(f"{serviceip}/login/{con_uuid}/step/4")

    # Keep the raw response bytes (sign_challenge_otp accepts bytes)
    step4_bytes = step4response.content
    try:
        step4_json = step4response.json()
    except Exception:
        step4_json = None

    # Load saved working file to find associated sv/svu
    save_location = os.getenv("BASE_SAVE_DIR", "./storage")
    working_file = Path(save_location) / "workingfiles" / f"{con_uuid}.json"
    if not working_file.exists():
        print(f"Working file not found: `{working_file.resolve()}`")
        return None

    with open(working_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        # Working files may be stored as a dict or as a list containing one dict
        if isinstance(data, dict):
            wf = data
        elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            wf = data[0]
        else:
            print(f"Unexpected working file format in {working_file}")
            return None

        # Try multiple possible key names and fall back to nested context
        sv_uuid = wf.get("sv_uuid") or wf.get("serviceuuid") or wf.get("service_uuid")
        svu_uuid = wf.get("svu_uuid") or wf.get("svuUUID") or wf.get("svuUuid") or wf.get("svu_uuid")
        if not sv_uuid or not svu_uuid:
            ctx = wf.get("context") or {}
            sv_uuid = sv_uuid or ctx.get("sv_uuid") or ctx.get("serviceuuid")
            svu_uuid = svu_uuid or ctx.get("svu_uuid") or ctx.get("svuUUID") or ctx.get("service_user_uuid")

        # Fallback: try to extract from the server step-4 JSON response if present
        if (not sv_uuid or not svu_uuid) and step4_json is not None:
            if isinstance(step4_json, list) and len(step4_json) > 0 and isinstance(step4_json[0], dict):
                resp_obj = step4_json[0]
            elif isinstance(step4_json, dict):
                resp_obj = step4_json
            else:
                resp_obj = {}

            sv_uuid = sv_uuid or resp_obj.get("sv_uuid") or resp_obj.get("serviceuuid") or resp_obj.get("service_uuid")
            svu_uuid = svu_uuid or resp_obj.get("svu_uuid") or resp_obj.get("svuUUID") or resp_obj.get("svuUuid") or resp_obj.get("svu_uuid")

        if not sv_uuid or not svu_uuid:
            print(f"Could not determine sv_uuid/svu_uuid from working file {working_file} or server response")
            return None
    user_file = Path(save_location) / "userfiles" / sv_uuid / f"{svu_uuid}.json"
    if not user_file.exists():
        print(f"User file not found: `{user_file.resolve()}`")
        return None

    with open(user_file, "r", encoding="utf-8") as f2:
        data = json.load(f2)
        # Accept either key name: older code stored 'otp_privK', other code expects 'otp_privkey'
        otp_privK_b64 = data.get("otp_privkey") or data.get("otp_privK") or data.get("otp_privKey")

    if otp_privK_b64 is None:
        print(f"No 'otp_privkey' in user file: {user_file}")
        return None

    try:
        otp_privK_bytes = base64.b64decode(otp_privK_b64)
    except Exception as e:
        print(f"Failed to decode otp_privkey from base64: {e}")
        return None

    # Call the OTP signer with the raw response bytes so it can parse JSON or handle bytes
    try:
        signed = sign_challenge_otp(otp_privK_bytes, step4_bytes)
        print("OTP signed successfully, length:", len(signed))
    except Exception as e:
        print("Failed to sign OTP challenge:", e)
        return None


    # Return both the raw signed bytes and the original payload bytes so caller can send what the server expects
    return signed, step4_bytes



def otp_return(con_uuid, signed_otp, payload_json_bytes):
    # Ensure payload_json is a UTF-8 string
    if isinstance(payload_json_bytes, bytes):
        try:
            payload_json_text = payload_json_bytes.decode('utf-8')
        except UnicodeDecodeError:
            payload_json_text = payload_json_bytes.decode('utf-8', errors='surrogatepass')
    elif isinstance(payload_json_bytes, str):
        payload_json_text = payload_json_bytes
    else:
        # Fallback to JSON-encoding the object
        payload_json_text = json.dumps(payload_json_bytes)

    payload = {
        "payload_json": payload_json_text,
        "signature": base64.b64encode(signed_otp).decode("ascii")
    }

    # Use requests' json= parameter so Content-Type: application/json is set
    returned = requests.post(f"{serviceip}/login/{con_uuid}/step/4.5", json=payload)
    return returned.json()



def login_processor(sv_uuid: str, svu_uuid: str, serviceip: str) -> Optional[str]:
    """Initialize the working file for a login attempt.

    This calls `save_workingfiles` using the UUIDs provided and returns the saved
    filename (or None if saving failed).
    """
    # Pass the supplied UUIDs so `save_workingfiles` doesn't prompt again.
    saved = save_workingfiles(serviceip, sv_uuid=sv_uuid, svu_uuid=svu_uuid)
    if saved:
        print(f"Working file saved to: {saved}")
        # Derive con_uuid from the saved filename (stem without extension)
        con_uuid = Path(saved).stem
        result = keymatch(sv_uuid, svu_uuid, con_uuid)
        print(result)
        kp_result = keypair(sv_uuid, svu_uuid, con_uuid)
        if kp_result is None:
            # stop flow if keypair step couldn't complete
            return saved
        otp_result = otp(con_uuid)
        if otp_result is not None:
            # otp() now returns (signed_otp, payload_bytes)
            try:
                signed_otp, payload_bytes = otp_result
            except Exception:
                print("Unexpected otp() return shape; expected (signed_bytes, payload_bytes)")
                return saved
            returned = otp_return(con_uuid, signed_otp, payload_bytes)
            print(returned)

            returned_status = returned.get("status")
            time_of_last_completion = returned.get("time_of_last_completion")
            step_name = returned.get("step_name")


            update_workingfile_status(con_uuid, time_of_last_completion, step_name, returned_status)

            return returned_status


    else:
        print("Working file was not saved.")
    return saved