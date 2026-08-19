import os
import time
import requests

def publish_instagram_reel(video_public_url, caption):
    ig_user_id = os.environ.get("IG_USER_ID")
    access_token = os.environ.get("IG_ACCESS_TOKEN")

    if not all([ig_user_id, access_token]):
        raise ValueError("Missing IG_USER_ID or IG_ACCESS_TOKEN in environment.")

    container_url = f"https://graph.facebook.com/v26.0/{ig_user_id}/media"
    payload = {"media_type": "REELS", "video_url": video_public_url, "caption": caption, "access_token": access_token}

    res = requests.post(container_url, data=payload, timeout=30)
    res.raise_for_status()
    container_id = res.json().get("id")

    if not container_id:
        raise RuntimeError(f"Failed to obtain container ID: {res.text}")

    status_url = f"https://graph.facebook.com/v26.0/{container_id}"
    max_checks = 30

    for check in range(1, max_checks + 1):
        status_res = requests.get(status_url, params={"fields": "status_code", "access_token": access_token}, timeout=15)
        status_res.raise_for_status()
        code = status_res.json().get("status_code")
        print(f"[Instagram] Container status check ({check}/{max_checks}): {code}")

        if code == "FINISHED":
            break
        elif code in ["ERROR", "EXPIRED"]:
            raise RuntimeError(f"Instagram container processing failed with code: {code}")
        time.sleep(10)
    else:
        raise RuntimeError("Instagram processing timed out.")

    pub_url = f"https://graph.facebook.com/v26.0/{ig_user_id}/media_publish"
    pub_res = requests.post(pub_url, data={"creation_id": container_id, "access_token": access_token}, timeout=30)
    pub_res.raise_for_status()
    media_id = pub_res.json().get("id")
    print(f"[Instagram] Reel published! Media ID: {media_id}")
    return media_id
