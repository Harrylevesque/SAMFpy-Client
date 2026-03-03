
import json
import os
from pathlib import Path
from dotenv import load_dotenv
import requests
from saving.workingfiles import update_workingfile_status

load_dotenv()
serviceip = os.getenv("host") or "http://localhost:8000"

BASE_DIR = Path(__file__).resolve().parents[1]

def keymatch(sv_uuid, svu_uuid, con_uuid):
    wf = BASE_DIR / "storage" / "workingfiles" / f"{con_uuid}.json"
    if not wf.exists():
        print(f"Working file not found: `{wf.resolve()}`.")
        return None

    try:
        with wf.open("r") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON in `{wf.resolve()}`: {e}")
        return None

    # Normalize to a dict record that has a 'status' key
    record = None
    if isinstance(data, dict):
        record = data
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and "status" in item:
                record = item
                break
        if record is None and len(data) > 0 and isinstance(data[0], dict):
            record = data[0]
    else:
        print(f"Unexpected JSON structure in `{wf.resolve()}` (expected dict or list).")
        return None

    if record.get("status") != "requested":
        return None
    uf = BASE_DIR / "storage" / "userfiles" / sv_uuid / f"{svu_uuid}.json"
    if not uf.exists():
        print(f"User file not found: `{uf.resolve()}`.")
        return None

    try:
        with uf.open("r") as f2:
            data2 = json.load(f2)
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON in `{uf.resolve()}`: {e}")
        return None

    pubk = data2.get("pubk")
    if not pubk:
        print("No `pubk` found in user file.")
        return None

    url = f"{serviceip.rstrip('/')}/login/{con_uuid}/step/2"
    try:
        resp = requests.post(url, json={"pubkey": pubk}, timeout=100)
        resp.raise_for_status()
        result = resp.json()

        update_workingfile_status(
            con_uuid=con_uuid,
            status=result.get("status", "keymatch_complete"),
            step_name="keymatch",
            time_of_last_completion=result.get("time_of_last_completion"),
        )

        return result
    except requests.RequestException as e:
        print(f"Request to `{url}` failed: {e}")
        return None