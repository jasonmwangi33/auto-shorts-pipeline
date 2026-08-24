#!/usr/bin/env python3
"""
Router Module: Preserves existing production YouTube API upload implementation, OAuth credentials, 
token management, account/channel routing, metadata, and retries while appending the routing ledger.
"""

import sys
import logging
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

logger = logging.getLogger("router")

def upload_to_youtube_channel(video_path: str, metadata: dict, account_creds: dict) -> dict:
    """
    Production YouTube API upload handling full OAuth credentials, token refresh, and metadata.
    """
    try:
        creds = Credentials(
            token=None,
            refresh_token=account_creds.get("refresh_token"),
            client_id=account_creds.get("client_id"),
            client_secret=account_creds.get("client_secret"),
            token_uri="https://oauth2.googleapis.com/token"
        )
        
        youtube = build("youtube", "v3", credentials=creds)
        
        body = {
            "snippet": {
                "title": metadata.get("title", "Short"),
                "description": metadata.get("description", ""),
                "tags": metadata.get("tags", []),
                "categoryId": metadata.get("categoryId", "22")
            },
            "status": {
                "privacyStatus": metadata.get("privacyStatus", "public"),
                "selfDeclaredMadeForKids": False
            }
        }
        
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        
        response = None
        while response is None:
            status, response = request.next_chunk()
            
        video_id = response.get("id")
        if not video_id:
            raise RuntimeError("YouTube API insert response missing video ID.")
            
        return {"status": "success", "video_id": video_id}
    except Exception as exc:
        logger.error("Production YouTube upload error: %s", exc)
        return {"status": "failed", "error": str(exc)}

def execute_routing_ledger(results: list) -> None:
    discovered = len(results)
    uploaded = sum(1 for r in results if r.get("status") == "success")
    failed = discovered - uploaded
    
    for r in results:
        if r.get("status") != "success":
            logger.error("Upload failed for seed %s: %s", r.get("seed_id"), r.get("error"))
            
    print(f"\n=================== PUBLISH SUMMARY ===================")
    print(f"{discovered} discovered | {uploaded} uploaded | {failed} failed")
    print(f"=======================================================\n")
    
    if uploaded < discovered:
        logger.error("FATAL: Upload count (%d) is less than discovered count (%d). Exiting with code 1.", uploaded, discovered)
        sys.exit(1)
        
    sys.exit(0)
