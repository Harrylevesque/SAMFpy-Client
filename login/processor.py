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
import time

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
        "challenge": challenge_b64,
    }

    try:
        # Send a real JSON body; using data=json.dumps(...) sends a raw string and can cause 422.
        keypair_valid = requests.post(
            f"{serviceip}/login/{con_uuid}/step/3.5",
            json=data3_5,
            timeout=30,
        )
        keypair_valid.raise_for_status()
        keypair_valid_json = keypair_valid.json()
    except requests.RequestException as e:
        print(f"Step 3.5 request failed: {e}")
        return None
    except ValueError as e:
        print(f"Step 3.5 returned non-JSON response: {e}")
        return None

    update_workingfile_status(
        con_uuid=con_uuid,
        status=keypair_valid_json.get("status", "keypair_complete"),
        step_name="keypair",
        time_of_last_completion=keypair_valid_json.get("time_of_last_completion"),
    )

    print(keypair_valid.text)
    return keypair_valid_json


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





def webauthn(con_uuid):


    start = requests.get(f"{serviceip}/webauthn/auth/start?mode=authenticate&con-uuid={con_uuid}")
    print(start.text)

    if start is not None:
        import webbrowser

        # Find the working file from several likely base locations (respect BASE_SAVE_DIR)
        candidates = [Path(os.getenv("BASE_SAVE_DIR", "./storage")), Path.cwd() / "storage", Path("/storage")]
        # Also try project-root storage if available
        try:
            project_root = Path(__file__).resolve().parents[1]
            candidates.insert(1, project_root / "storage")
        except Exception:
            pass

        wf_path = None
        tried = []
        for base in candidates:
            wf_candidate = base / "workingfiles" / f"{con_uuid}.json"
            tried.append(str(wf_candidate))
            if wf_candidate.exists():
                wf_path = wf_candidate
                break
            alt = base / "workingfiles" / con_uuid
            tried.append(str(alt))
            if alt.exists():
                wf_path = alt
                break

        if wf_path is None:
            print("webauthn: working file not found. Tried:")
            for p in tried:
                print("  ", p)
            return

        # Load the working file and accept dict or list formats
        with open(wf_path, "r", encoding="utf-8") as f:
            data = json.load(f)

            # Helper: recursively search dicts/lists for sv_uuid and svu_uuid
            def recursive_find(obj):
                sv = None
                svu = None

                if isinstance(obj, dict):
                    # direct keys first
                    sv = obj.get("sv_uuid") or obj.get("serviceuuid") or obj.get("service_uuid") or obj.get("serviceUuid")
                    svu = (
                        obj.get("svu_uuid") or obj.get("svuUUID") or obj.get("svuUuid") or obj.get("svu") or obj.get("service_user_uuid")
                    )
                    if sv and svu:
                        return sv, svu
                    # fallback to context
                    ctx = obj.get("context")
                    if isinstance(ctx, dict):
                        sv = sv or ctx.get("sv_uuid") or ctx.get("serviceuuid") or ctx.get("service_uuid")
                        svu = svu or ctx.get("svu_uuid") or ctx.get("svuUUID") or ctx.get("svuUuid") or ctx.get("service_user_uuid")
                        if sv and svu:
                            return sv, svu

                    # recurse into values
                    for v in obj.values():
                        try_sv, try_svu = recursive_find(v)
                        if try_sv and not sv:
                            sv = try_sv
                        if try_svu and not svu:
                            svu = try_svu
                        if sv and svu:
                            return sv, svu

                elif isinstance(obj, list):
                    for item in obj:
                        try_sv, try_svu = recursive_find(item)
                        if try_sv and not sv:
                            sv = try_sv
                        if try_svu and not svu:
                            svu = try_svu
                        if sv and svu:
                            return sv, svu

                return sv, svu

            sv_uuid, svu_uuid = recursive_find(data)

            if not sv_uuid or not svu_uuid:
                print("webauthn: could not determine sv_uuid or svu_uuid from working file (after recursive search)")
                print("  sv_uuid:", sv_uuid)
                print("  svu_uuid:", svu_uuid)
                return

        # Open the registration UI (URL may need adjustment depending on server)
        url = f"{serviceip}?mode=authentication&con-uuid={con_uuid}"
        webbrowser.open(url)
        print(url)

    # end if start is not None
    pass


def check_if_complete(serviceip, con_uuid):
    status_resp = requests.get(f"{serviceip}/session/{con_uuid}")
    try:
        status_json = status_resp.json()
    except Exception as e:
        # Couldn't parse JSON at all
        print(f"Failed to parse status response as JSON: {e}")
        print("Response text:", status_resp.text)
        return False

    # Normalize into a list of dicts we can safely inspect
    items = []
    if isinstance(status_json, dict):
        items = [status_json]
    elif isinstance(status_json, list):
        # keep only dict elements
        items = [it for it in status_json if isinstance(it, dict)]
    elif isinstance(status_json, str):
        # Sometimes APIs return a JSON-encoded string; try to parse it
        try:
            inner = json.loads(status_json)
            if isinstance(inner, dict):
                items = [inner]
            elif isinstance(inner, list):
                items = [it for it in inner if isinstance(it, dict)]
            else:
                print(f"Status response is a JSON string but contains unexpected type: {type(inner)}")
                print("Response text:", status_json)
                return False
        except Exception:
            print("Status response is a plain string, not JSON object/list:", status_json)
            return False
    else:
        print(f"Unexpected status response type: {type(status_json)}")
        print("Response text:", status_resp.text)
        return False

    def step_complete(step_name: str) -> bool:
        """Return True if any item indicates the given step has status 'complete'."""
        for item in items:
            # item is guaranteed to be a dict here
            steps = item.get("steps") if isinstance(item.get("steps"), dict) else {}
            step_obj = steps.get(step_name) if isinstance(steps.get(step_name), dict) else {}
            status = step_obj.get("status") if isinstance(step_obj.get("status"), str) else ""
            if status.lower() == "complete":
                return True
        return False

    keymatch_complete = step_complete("keymatch")
    webauthn_complete = step_complete("webauthn")
    keypair_complete = step_complete("keypair")
    otp_complete = step_complete("otp")

    if keymatch_complete and webauthn_complete and keypair_complete and otp_complete:
        print("complete")
        return "complete"
    else:
        return "failed"


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

            returned_status = returned.get("status") or ("complete" if returned.get("signature_valid") else "otp_failed")
            time_of_last_completion = returned.get("time_of_last_completion")
            step_name = returned.get("step_name") or "otp"

            update_workingfile_status(
                con_uuid=con_uuid,
                status=returned_status,
                step_name=step_name,
                time_of_last_completion=time_of_last_completion,
            )

            # If OTP step succeeded (signature validated or returned 'complete'), trigger webauthn flow
            if returned.get("signature_valid") or returned_status == "complete":
                try:
                    webauthn(con_uuid)
                except Exception as e:
                    print(f"webauthn call failed: {e}")


            first_check = check_if_complete(serviceip, con_uuid)
            while first_check != "complete":
                print("Waiting for completion...")
                time.sleep(1)
                first_check = check_if_complete(serviceip, con_uuid)

            return returned_status




    else:
        print("Working file was not saved.")
    return saved
