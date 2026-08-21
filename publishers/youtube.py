import json
import os
import logging
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

logger = logging.getLogger("youtube_publisher")

def upload_to_youtube_channel(account_num: int, video_path: str, title: str, description: str):
    bundle_json = os.getenv("YOUTUBE_ACCOUNTS_JSON")
    if not bundle_json:
        raise ValueError("YOUTUBE_ACCOUNTS_JSON secret is not set in environment.")

    accounts = json.loads(bundle_json)
    acc_key = str(account_num)
    if acc_key not in accounts:
        raise ValueError(f"Account {account_num} not found in YOUTUBE_ACCOUNTS_JSON bundle.")

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

    media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = request.execute()

    video_id = response.get("id")
    logger.info(f"Successfully uploaded video ID: {video_id} (Public) to Account {account_num}")
    return video_id, acc_data.get("channel_id", "")
