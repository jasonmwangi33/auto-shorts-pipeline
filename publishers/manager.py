import os
from publishers.state import calculate_video_hash, get_target_status, update_target_state
from publishers.youtube import upload_to_youtube_channel
from publishers.instagram import publish_instagram_reel

MAX_YOUTUBE_ACCOUNTS = 6

def publish_qc_video(video_path, job_id, qc_passed, title, youtube_description, instagram_caption, video_public_url=None):
    print("=" * 60)
    
    if not qc_passed:
        raise ValueError(f"Publishing blocked: QC pass status is False for job {job_id}")

    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Video file not found at: {video_path}")

    video_hash = calculate_video_hash(video_path)
    print(f"Video SHA-256: {video_hash}")

    report = {"job_id": job_id, "video_hash": video_hash, "targets": {}}

    for account_num in range(1, MAX_YOUTUBE_ACCOUNTS + 1):
        target_key = f"youtube_{account_num}"
        current_status = get_target_status(video_hash, target_key)

        if current_status == "SUCCESS":
            print(f"[Skip] {target_key} already published.")
            report["targets"][target_key] = "ALREADY_PUBLISHED"
            continue

        try:
            print(f"Processing {target_key}...")
            video_id, channel_id = upload_to_youtube_channel(account_num, video_path, title, youtube_description)
            update_target_state(video_hash, target_key, "SUCCESS", platform_id=video_id, details={"channel_id": channel_id})
            report["targets"][target_key] = f"SUCCESS (ID: {video_id})"
        except Exception as e:
            print(f"[Error] {target_key} failed: {e}")
            update_target_state(video_hash, target_key, "FAILED", details={"error": str(e)})
            report["targets"][target_key] = f"FAILED ({e})"

    ig_target_key = "instagram"
    if not video_public_url:
        print("[Instagram] Skipped: No public video URL provided.")
        report["targets"][ig_target_key] = "SKIPPED_NO_PUBLIC_URL"
    else:
        ig_status = get_target_status(video_hash, ig_target_key)
        if ig_status == "SUCCESS":
            print("[Skip] Instagram Reel already published.")
            report["targets"][ig_target_key] = "ALREADY_PUBLISHED"
        else:
            try:
                print("Processing Instagram Reel...")
                media_id = publish_instagram_reel(video_public_url, instagram_caption)
                update_target_state(video_hash, ig_target_key, "SUCCESS", platform_id=media_id)
                report["targets"][ig_target_key] = f"SUCCESS (ID: {media_id})"
            except Exception as e:
                print(f"[Error] Instagram failed: {e}")
                update_target_state(video_hash, ig_target_key, "FAILED", details={"error": str(e)})
                report["targets"][ig_target_key] = f"FAILED ({e})"

    print("\n" + "=" * 60)
    print("PUBLISHING REPORT SUMMARY")
    print("=" * 60)
    for target, result in report["targets"].items():
        print(f"  {target.ljust(15)} : {result}")
    print("=" * 60)

    return report
