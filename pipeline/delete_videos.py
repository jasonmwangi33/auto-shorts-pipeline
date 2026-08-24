import os
import json
import logging
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("deleter")

def get_youtube_service():
    """Builds authenticated YouTube API client from environment secrets."""
    tokens_json = os.environ.get("YOUTUBE_ACCOUNTS_JSON")
    if not tokens_json:
        raise RuntimeError("YOUTUBE_ACCOUNTS_JSON secret not found!")
    
    accounts = json.loads(tokens_json)
    # Use the primary account credentials
    acc = accounts[0] if isinstance(accounts, list) else list(accounts.values())[0]
    
    creds = Credentials(
        token=acc.get("access_token"),
        refresh_token=acc.get("refresh_token"),
        client_id=acc.get("client_id"),
        client_secret=acc.get("client_secret"),
        token_uri="https://oauth2.googleapis.com/token"
    )
    return build("youtube", "v3", credentials=creds)

def delete_channel_videos(limit: int = 10):
    """Deletes recent videos from the authenticated channel."""
    youtube = get_youtube_service()
    
    # Get channel's uploads playlist
    channels_response = youtube.channels().list(mine=True, part="contentDetails").execute()
    uploads_playlist_id = channels_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    
    logger.info(f"Fetching recent videos from uploads playlist...")
    playlist_response = youtube.playlistItems().list(
        playlistId=uploads_playlist_id,
        part="snippet",
        maxResults=limit
    ).execute()
    
    items = playlist_response.get("items", [])
    if not items:
        logger.info("No videos found to delete.")
        return
        
    for item in items:
        video_id = item["snippet"]["resourceId"]["videoId"]
        title = item["snippet"]["title"]
        logger.info(f"Deleting video: '{title}' (ID: {video_id})")
        try:
            youtube.videos().delete(id=video_id).execute()
            logger.info(f"Successfully deleted: {video_id}")
        except Exception as e:
            logger.error(f"Failed to delete {video_id}: {e}")

if __name__ == "__main__":
    # Deletes up to 15 recent test videos by default
    delete_channel_videos(limit=15)
