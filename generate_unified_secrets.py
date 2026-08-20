import json
import os
import sys
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly"
]

def process_all_accounts():
    accounts_bundle = []

    for i in range(1, 8):
        secret_file = f"client_secret_{i}.json"
        if not os.path.exists(secret_file):
            print(f"[-] Skipping {secret_file} (File not found)")
            continue

        print(f"\n" + "="*50)
        print(f" Authorizing Account #{i} of 7")
        print("="*50)
        print(f"Opening browser for Account #{i}. Sign in to your Google Account...\n")

        with open(secret_file, "r") as f:
            secret_data = json.load(f)
            client_config = secret_data.get("installed") or secret_data.get("web")
            client_id = client_config.get("client_id")
            client_secret = client_config.get("client_secret")

        flow = InstalledAppFlow.from_client_secrets_file(secret_file, SCOPES)
        
        # Reverted to auto-open the browser
        creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")

        # Fetch channel ID and Title automatically
        youtube = build("youtube", "v3", credentials=creds)
        chan_res = youtube.channels().list(part="id,snippet", mine=True).execute()
        items = chan_res.get("items", [])
        
        channel_id = items[0]["id"] if items else "UNKNOWN"
        channel_title = items[0]["snippet"]["title"] if items else "UNKNOWN"

        print(f"[+] Account #{i} Verified: '{channel_title}' (ID: {channel_id})")

        accounts_bundle.append({
            "account_num": i,
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": creds.refresh_token,
            "channel_id": channel_id,
            "channel_title": channel_title
        })

    # Save to a single bundle file
    output_file = "youtube_accounts_bundle.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(accounts_bundle, f, indent=2)

    print("\n" + "#"*60)
    print(" ALL 7 ACCOUNTS PROCESSED SUCCESSFULLY!")
    print(f" Saved to {output_file}")
    print("#"*60)

if __name__ == "__main__":
    process_all_accounts()
