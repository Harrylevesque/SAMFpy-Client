from flask.cli import load_dotenv

from saving.workingfiles import save_workingfiles
from login.keymatch import keymatch
from login.keypair import sign_challenge
from saving.workingfiles import update_workingfile_status

from pathlib import Path
from typing import Optional
import json
import os
import requests
import base64

load_dotenv()

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
    signature = sign_challenge(privK_bytes, challenge)
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
        keypair(sv_uuid, svu_uuid, con_uuid)
    else:
        print("Working file was not saved.")
    return saved