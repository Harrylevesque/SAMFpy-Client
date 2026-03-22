import json

async def sustain(con_uuid):
    with open(f"workingfiles/{con_uuid}.", "r") as f:
        sustain_time = int(f.read().strip())