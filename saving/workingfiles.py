import requests
import json
from pathlib import Path
from typing import Optional
import uuid

# Determine project root relative to this file and create storage/workingfiles there

BASE_DIR = Path(__file__).resolve().parents[1]
storage_dir = BASE_DIR / "storage" / "workingfiles"
storage_dir.mkdir(parents=True, exist_ok=True)
save_location = str(storage_dir)


from dotenv import load_dotenv
import os
load_dotenv()

serviceip = os.getenv("host")

def save_workingfiles(serviceip: str, sv_uuid: Optional[str] = None, svu_uuid: Optional[str] = None, con_uuid: Optional[str] = None) -> Optional[str]:
    """Fetch working file step data and save to storage.

    If any of sv_uuid, svu_uuid, con_uuid are None, prompt the user.
    Returns the path to the saved file on success, or None on failure.
    """
    if sv_uuid is None or sv_uuid.strip() == "":
        sv_uuid = input("Enter the service UUID: ").strip()
    if svu_uuid is None or svu_uuid.strip() == "":
        svu_uuid = input("Enter the service-user (svu) UUID: ").strip()
    if con_uuid is None or con_uuid.strip() == "":
        con_uuid = f"con--{uuid.uuid4()}".strip()

    def ensure_scheme(url: str) -> str:
        if not url.startswith(("http://", "https://")):
            return "http://" + url
        return url

    base = ensure_scheme(serviceip).rstrip('/')
    url = f"{base}/service/{sv_uuid}/user/{svu_uuid}/{con_uuid}/step/1"

    try:
        resp = requests.get(url, timeout=10)
        print(f"Status: {resp.status_code}")
        print("Headers:", resp.headers)

        try:
            data = resp.json()
            print("JSON response:")
            print(json.dumps(data, indent=2))

            # Get con_uuid from nested context, fall back to argument or svu_uuid
            ctx = data.get("context", {}) if isinstance(data, dict) else {}
            resp_con_uuid = (ctx.get("con_uuid") or "").strip()
            # prefer a non-empty value from response, otherwise use provided con_uuid or svu_uuid
            con_uuid_final = resp_con_uuid or (con_uuid or "").strip() or (svu_uuid or "").strip()
            if not con_uuid_final:
                print("No connection UUID available to name the file; aborting save.")
                return None

            target_file = Path(save_location) / f"{con_uuid_final}.json"
            with open(target_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            print(f"Saved working file to: {target_file}")
            return str(target_file)

        except ValueError:
            print("Non-JSON response:")
            print(resp.text)
            return None
    except requests.RequestException as e:
        print("Request failed:", e)
        return None


def update_workingfile_status(con_uuid: str, status: str, step_name: str, time_of_last_completion: float = None) -> bool:
    """Update the status and time_of_last_completion for a given step in the working file.

    Args:
        con_uuid: Connection UUID (filename stem)
        status: New status string
        step_name: Step name (e.g., 'keymatch', 'keypair', 'otp')
        time_of_last_completion: Optional timestamp from the server response
    """
    file_path = storage_dir / f"{con_uuid}.json"
    if not file_path.exists():
        raise FileNotFoundError(f"Working file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Handle both list and dict formats
    if isinstance(data, dict):
        target = data
    elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
        target = data[0]
    else:
        raise ValueError(f"Invalid working file format in {file_path}")

    target["status"] = status
    if time_of_last_completion is not None:
        target["time_of_last_completion"] = time_of_last_completion
    target["last_step_updated"] = step_name
    if "steps" in target and isinstance(target["steps"], dict):
        target["steps"][step_name] = {
            "status": "complete",
            "time_of_last_completion": time_of_last_completion,
        }

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    return True


if __name__ == "__main__":
    # When run directly, ask for `serviceip` then call save_workingfiles
    save_workingfiles(serviceip)


