#!/usr/bin/env python3
"""
Crash-proof autosave helper.
Run this after every important action: python3 scripts/save_checkpoint.py "what we just did"
"""
import json, datetime, os, sys

msg = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "autosave"

# Update checkpoint.json
with open("/home/user/checkpoint.json", "r") as f:
    data = json.load(f)
data["last_updated"] = datetime.datetime.now().isoformat()
data["last_action"] = msg
data["turn_number"] = data.get("turn_number", 0) + 0.1  # fractional for mid-turn
with open("/home/user/checkpoint.json", "w") as f:
    json.dump(data, f, indent=2)

# Append to TURN_LOG
with open("/home/user/TURN_LOG.md", "a") as f:
    f.write(f"\n**[AUTOSAVE {data['last_updated']}]** {msg}\n")

# Also snapshot to memory/autosaves
stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
with open(f"/home/user/memory/autosaves/autosave_{stamp}.txt", "w") as f:
    f.write(f"{data['last_updated']} - {msg}\n")
    f.write(json.dumps(data, indent=2))

print(f"✅ Autosaved: {msg}")
