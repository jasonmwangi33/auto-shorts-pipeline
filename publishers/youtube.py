import json
import os
import random
import time
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

def upload_to_youtube_channel(account_num, video_path, title, description):
    raw_bundle = os.environ.get("YOUTUBE_ACCOUNTS_JSON")
    if not raw_bundle:
        raise ValueError("Missing YOUTUBE_ACCOUNTS_JSON in environment variables.")

    accounts_list = json.loads(raw_bundle)
    
    # Find the specific account in the JSON bundle
    target_account = next((acc for acc in accounts_list if acc.get("account_num") == account_num), None)
    if not target_account:
        raise ValueError(f"Account #{account_num} configuration not found in YOUTUBE_ACCOUNTS_JSON")

    client_id = target_account.get("client_id")
    client_secret = target_account.get("client_secret")
    refresh_token = target_account.get("refresh_token")

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token"
    )

    youtube = build("youtube", "v3", credentials=creds)

    # Verify channel identity
    channel_res = youtube.channels().list(part="id,snippet", mine=True).execute()
    items = channel_res.get("items", [])
    if not items:
        raise RuntimeError(f"[YT{account_num}] Could not retrieve channel info.")

    actual_channel_id = items[0]["id"]
    channel_title = items[0]["snippet"]["title"]
    print(f"[YT{account_num}] Verified: '{channel_title}' ({actual_channel_id})")

    body = {
        "snippet": {"title": title, "description": description, "categoryId": "22"},
        "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False}
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part=",".join(body.keys()), body=body, media_body=media)

    response = None
    max_retries = 5
    retry_count = 0

    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                print(f"[YT{account_num}] Upload progress: {int(status.progress() * 100)}%")
        except HttpError as e:
            if e.resp.status in [500, 502, 503, 504]:
                retry_count += 1
                if retry_count > max_retries:
                    raise RuntimeError(f"[YT{account_num}] Max retries exceeded: {e}")
                sleep_time = (2 ** retry_count) + random.uniform(0.5, 1.5)
                print(f"[YT{account_num}] Retrying in {sleep_time:.2f}s...")
                time.sleep(sleep_time)
            elif e.resp.status == 403 and "quotaExceeded" in str(e):
                raise RuntimeError(f"[YT{account_num}] Quota exceeded: {e}")
            else:
                raise RuntimeError(f"[YT{account_num}] HTTP Error: {e}")

    video_id = response.get("id")
    print(f"[YT{account_num}] Upload successful! Video ID: {video_id}")
    return video_id, actual_channel_id
