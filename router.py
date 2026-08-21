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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts-dir", type=str, default="artifacts")
    # FIX: Tell the script to accept the seeds-file argument from GitHub Actions
    parser.add_argument("--seeds-file", type=str, default="seeds.json") 
    args = parser.parse_args()

    artifacts_dir = Path(args.artifacts_dir)
    if not artifacts_dir.exists():
        logger.error(f"Artifacts directory not found: {artifacts_dir}")
        sys.exit(1)

    metadata_files = list(artifacts_dir.rglob("*_metadata.json"))
    if not metadata_files:
        logger.warning("No metadata files found. Nothing to publish.")
        return

    logger.info(f"[*] Found {len(metadata_files)} completed videos ready for publishing.")

    for meta_path in metadata_files:
        job_id = meta_path.name.replace("_metadata.json", "")
        video_path = meta_path.parent / f"{job_id}_output.mp4"
        qc_path = meta_path.parent / f"{job_id}_qc.json"

        if not video_path.exists():
            logger.error(f"[!] Missing video file for {job_id}")
            continue

        seed_index = 0
        if qc_path.exists():
            qc_data = json.loads(qc_path.read_text(encoding="utf-8"))
            seed_index = qc_data.get("seed_index", 0)
            if not qc_data.get("passed", False):
                logger.warning(f"[-] QC failed for {job_id}, skipping publish.")
                continue

        meta_data = json.loads(meta_path.read_text(encoding="utf-8"))
        title = meta_data.get("title", "Relatable Thoughts")
        description = meta_data.get("description", "")
        
        yt_account = ROUTES.get(seed_index, 1)

        logger.info(f"[*] Routing Video {job_id} -> YouTube Account {yt_account}")
        try:
            upload_to_youtube_channel(yt_account, str(video_path), title, description)
        except Exception as e:
            logger.error(f"[!] Failed to upload {job_id} to Account {yt_account}: {e}")

if __name__ == "__main__":
    main()
