import os
import random
import time
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

def upload_to_youtube_channel(account_num, video_path, title, description):
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    refresh_token = os.environ.get(f"YT_REFRESH_TOKEN_{account_num}")
    expected_channel_id = os.environ.get(f"YT_CHANNEL_ID_{account_num}")

    if not all([client_id, client_secret, refresh_token]):
        raise ValueError(f"Missing OAuth credentials for YouTube Account {account_num}")

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token"
    )

    youtube = build("youtube", "v3", credentials=creds)

    channel_res = youtube.channels().list(part="id,snippet", mine=True).execute()
    items = channel_res.get("items", [])
    if not items:
        raise RuntimeError(f"[YT{account_num}] Could not retrieve authenticated channel info.")

    actual_channel_id = items[0]["id"]
    channel_title = items[0]["snippet"]["title"]

    if expected_channel_id and actual_channel_id != expected_channel_id:
        raise ValueError(f"[YT{account_num}] Channel ID mismatch! Expected '{expected_channel_id}', authenticated as '{actual_channel_id}' ({channel_title})")

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
                print(f"[YT{account_num}] Transient HTTP {e.resp.status}. Backing off {sleep_time:.2f}s...")
                time.sleep(sleep_time)
            elif e.resp.status == 403 and "quotaExceeded" in str(e):
                raise RuntimeError(f"[YT{account_num}] Quota exceeded: {e}")
            else:
                raise RuntimeError(f"[YT{account_num}] Non-retryable HTTP error: {e}")

    video_id = response.get("id")
    print(f"[YT{account_num}] Upload successful! Video ID: {video_id}")
    return video_id, actual_channel_id
