import argparse
import json
import logging
from pathlib import Path
import sys
from publishers.youtube import upload_to_youtube_channel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("router")

ROUTES = {
    0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7
}

# The pool of all available YouTube accounts
ALL_ACCOUNTS = [1, 2, 3, 4, 5, 6, 7]

def load_state(state_file: Path) -> dict:
    if state_file.exists():
        return json.loads(state_file.read_text(encoding="utf-8"))
    return {}

def save_state(state_file: Path, state_data: dict):
    state_file.write_text(json.dumps(state_data, indent=2), encoding="utf-8")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts-dir", type=str, default="artifacts")
    parser.add_argument("--seeds-file", type=str, default="seeds.json") 
    args = parser.parse_args()

    artifacts_dir = Path(args.artifacts_dir)
    state_file = Path("publish_state.json")
    published_state = load_state(state_file)

    if not artifacts_dir.exists():
        logger.error(f"Artifacts directory not found: {artifacts_dir}")
        sys.exit(1)

    metadata_files = list(artifacts_dir.rglob("*_metadata.json"))
    if not metadata_files:
        logger.warning("No metadata files found. Nothing to publish.")
        return

    c_discovered = len(metadata_files)
    c_uploaded = 0
    c_failed = 0
    c_skipped = 0

    # Track which accounts have successfully received a video this run
    # to guarantee we keep them spread out (1 video per account)
    used_accounts = set()

    logger.info(f"[*] Discovered {c_discovered} metadata files for publishing evaluation.")

    for meta_path in metadata_files:
        job_id = meta_path.name.replace("_metadata.json", "")
        video_path = meta_path.parent / f"{job_id}_output.mp4"
        qc_path = meta_path.parent / f"{job_id}_qc.json"

        if job_id in published_state:
            logger.info(f"[SKIP] Video {job_id} is already marked as published in state file.")
            c_skipped += 1
            continue

        if not video_path.exists():
            logger.error(f"[FAIL] Missing video payload for {job_id}")
            c_failed += 1
            continue

        seed_index = 0
        if qc_path.exists():
            qc_data = json.loads(qc_path.read_text(encoding="utf-8"))
            seed_index = qc_data.get("seed_index", 0)
            if not qc_data.get("passed", False):
                logger.warning(f"[SKIP] QC explicitly failed for {job_id}. Bypassing upload.")
                c_skipped += 1
                continue

        meta_data = json.loads(meta_path.read_text(encoding="utf-8"))
        title = meta_data.get("title", "Relatable Thoughts")
        description = meta_data.get("description", "")
        
        # Determine the primary target account
        primary_account = ROUTES.get(seed_index, 1)
        
        # Build the fallback queue: Try primary first, then all other accounts
        fallback_queue = [primary_account] + [acc for acc in ALL_ACCOUNTS if acc != primary_account]
        
        uploaded_successfully = False

        for yt_account in fallback_queue:
            if yt_account in used_accounts:
                continue # Skip accounts that already got a video to ensure spread

            logger.info(f"[*] Initiating Upload: Video {job_id} -> YouTube Account {yt_account}")
            try:
                video_id, channel_id = upload_to_youtube_channel(yt_account, str(video_path), title, description)
                logger.info(f"[SUCCESS] {job_id} live at https://youtube.com/shorts/{video_id}")
                
                published_state[job_id] = {"video_id": video_id, "channel": channel_id}
                save_state(state_file, published_state)
                
                used_accounts.add(yt_account) # Lock this account so it doesn't get duplicate videos
                c_uploaded += 1
                uploaded_successfully = True
                break # Success! Break out of the fallback loop and move to the next video
                
            except Exception as e:
                logger.warning(f"[-] Upload failed for Account {yt_account}: {str(e)}. Attempting next backup account...")

        if not uploaded_successfully:
            logger.error(f"[FAIL] Video {job_id} exhausted all backup accounts. Could not be uploaded.")
            c_failed += 1

    print("\n================ PUBLISH SUMMARY ================")
    print(f"{c_discovered} discovered | {c_uploaded} uploaded | {c_skipped} skipped | {c_failed} failed")
    print("=================================================\n")

    if c_failed > 0 or (c_uploaded + c_skipped < c_discovered):
        logger.error("Publishing constraints not met. Exiting with fatal code.")
        sys.exit(1)

if __name__ == "__main__":
    main()
