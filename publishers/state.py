import hashlib
import json
import os

STATE_FILE = "upload_state.json"

def calculate_video_hash(filepath, chunk_size=65536):
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

def get_target_status(video_hash, target_key):
    state = load_state()
    return state.get(video_hash, {}).get(target_key, {}).get("status", "NOT_STARTED")

def update_target_state(video_hash, target_key, status, platform_id=None, details=None):
    state = load_state()
    if video_hash not in state:
        state[video_hash] = {}
    state[video_hash][target_key] = {
        "status": status,
        "platform_id": platform_id,
        "details": details or {}
    }
    save_state(state)
