import json
import os
import logging
import traceback
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

logger = logging.getLogger("youtube_publisher")

def upload_to_youtube_channel(account_num: int, video_path: str, title: str, description: str):
    bundle_json = os.getenv("YOUTUBE_ACCOUNTS_JSON")
    if not bundle_json:
        raise ValueError("CRITICAL: YOUTUBE_ACCOUNTS_JSON secret is missing from GitHub environment variables.")

    try:
        accounts = json.loads(bundle_json)
    except Exception as e:
        raise ValueError(f"CRITICAL: Failed to parse YOUTUBE_ACCOUNTS_JSON as valid JSON. Error: {e}")

    print(f"[*] Loaded accounts JSON successfully. Available keys/type: {list(accounts.keys()) if isinstance(accounts, dict) else type(accounts)}")

    try:
        # SMART FALLBACK: If the user provided a single credential object instead of a numbered bundle
        if isinstance(accounts, dict) and "client_id" in accounts:
            acc_data = accounts
        else:
            acc_key = str(account_num)
            if acc_key not in accounts:
                raise KeyError(f"Account key '{acc_key}' not found in YOUTUBE_ACCOUNTS_JSON keys: {list(accounts.keys())}")
            acc_data = accounts[acc_key]

        creds = Credentials(
            token=None,
            refresh_token=acc_data["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=acc_data["client_id"],
            client_secret=acc_data["client_secret"]
        )

        youtube = build("youtube", "v3", credentials=creds)

        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:4000],
                "tags": ["Shorts", "RedditStories", "Viral"],
                "categoryId": "24"
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False
            }
        }

        print(f"[*] Initiating YouTube upload for account {account_num} with video path: {video_path}")
        media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        response = request.execute()

        video_id = response.get("id")
        print(f"[SUCCESS] Uploaded to YouTube. Video ID: {video_id}")
        return video_id, acc_data.get("channel_id", "")

    except Exception as e:
        print("="*60)
        print(f"[-] CRITICAL YOUTUBE UPLOAD FAILURE ON ACCOUNT {account_num}")
        print(f"[-] Error Type: {type(e).__name__}")
        print(f"[-] Error Message: {str(e)}")
        print("[-] Full Stack Traceback:")
        traceback.print_exc()
        print("="*60)
        # Hard fail: re-raise so the build stops and exposes the exact reason
        raise
