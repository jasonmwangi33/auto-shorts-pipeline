import argparse, json, logging, os, subprocess, sys, time
from pathlib import Path
from publishers.youtube import upload_to_youtube_channel
from publishers.instagram import publish_instagram_reel
from publishers.state import update_target_state

logger = logging.getLogger("router")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

ROUTES = [
    {"seed_index": 0, "youtube_account": 1, "instagram": True},
    {"seed_index": 1, "youtube_account": 2, "instagram": False},
    {"seed_index": 2, "youtube_account": 3, "instagram": False},
    {"seed_index": 3, "youtube_account": 4, "instagram": False},
    {"seed_index": 4, "youtube_account": 5, "instagram": False},
    {"seed_index": 5, "youtube_account": 6, "instagram": False},
    {"seed_index": 6, "youtube_account": 7, "instagram": False},
]

def find_qc_manifest(artifacts_dir, seed_index):
    for qc_path in artifacts_dir.glob("output/*_qc.json"):
        try:
            if json.loads(qc_path.read_text(encoding="utf-8")).get("seed_index") == seed_index:
                return qc_path
        except Exception: continue
    return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts-dir", type=str, default="artifacts")
    parser.add_argument("--seeds-file", type=str, default="seeds.json")
    args = parser.parse_args()

    artifacts_dir = Path(args.artifacts_dir)
    seeds_path = Path(args.seeds_file)
    if not seeds_path.exists(): seeds_path = artifacts_dir / "seeds" / "seeds.json"
    seeds = json.loads(seeds_path.read_text(encoding="utf-8"))

    for route in ROUTES:
        seed_index = route["seed_index"]
        seed = seeds[seed_index]
        qc_manifest_path = find_qc_manifest(artifacts_dir, seed_index)
        
        if not qc_manifest_path: continue
        qc = json.loads(qc_manifest_path.read_text(encoding="utf-8"))
        if not qc.get("passed"): continue

        video_path = qc_manifest_path.parent / Path(qc["output_file"]).name
        title = seed.get("headline", "Untitled")
        desc = f"{title} #Shorts"
        video_hash = qc.get("sha256")

        # 1. YouTube Upload
        account = route["youtube_account"]
        target_yt = f"youtube_{account}"
        try:
            logger.info(f"Routing Video {seed_index} to YouTube Account {account}")
            vid_id, chan_id = upload_to_youtube_channel(account, str(video_path), title, desc)
            update_target_state(video_hash, target_yt, "SUCCESS", platform_id=vid_id)
        except Exception as e:
            logger.error(f"YouTube {account} failed: {e}")

        # 2. Instagram Upload (Only if true)
        if route.get("instagram"):
            logger.info(f"Routing Video {seed_index} to Instagram")
            release_tag = f"temp-ig-{seed_index}-{int(time.time())}"
            try:
                # Automate the GitHub temporary hosting bridge securely
                subprocess.run(["gh", "release", "create", release_tag, str(video_path), "--title", release_tag, "--notes", "Temp IG Asset"], check=True)
                repo = os.getenv("GITHUB_REPOSITORY")
                public_url = f"https://github.com/{repo}/releases/download/{release_tag}/{video_path.name}"
                
                ig_id = publish_instagram_reel(public_url, desc)
                update_target_state(video_hash, "instagram", "SUCCESS", platform_id=ig_id)
            except Exception as e:
                logger.error(f"Instagram upload failed: {e}")
            finally:
                subprocess.run(["gh", "release", "delete", release_tag, "--cleanup-tag", "-y"], check=False)

if __name__ == "__main__": main()
