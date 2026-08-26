import os
from publishers.state import calculate_video_hash, get_target_status, update_target_state
from publishers.youtube import upload_to_youtube_channel
from publishers.instagram import publish_instagram_reel

def publish_qc_video(video_path, job_id, qc_passed, title, youtube_description, instagram_caption, video_public_url=None, target_account_num=1):
    print("=" * 60)

    if not qc_passed:
        raise ValueError(f"Publishing blocked: QC pass status is False for job {job_id}")

    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Video file not found at: {video_path}")

    video_hash = calculate_video_hash(video_path)
    print(f"Video SHA-256: {video_hash}")

    report = {"job_id": job_id, "video_hash": video_hash, "targets": {}}

    # STRICT ISOLATION: Only target the specific account requested
    target_key = f"youtube_{target_account_num}"
    current_status = get_target_status(video_hash, target_key)

    if current_status == "SUCCESS":
        print(f"[Skip] {target_key} already published.")
        report["targets"][target_key] = "ALREADY_PUBLISHED"
        return report

    try:
        print(f"Processing {target_key}...")
        video_id, channel_id = upload_to_youtube_channel(target_account_num, video_path, title, youtube_description)
        update_target_state(video_hash, target_key, "SUCCESS", platform_id=video_id, details={"channel_id": channel_id})
        report["targets"][target_key] = f"SUCCESS (ID: {video_id})"
    except Exception as e:
        print(f"[Hard-Fail Error] {target_key} failed: {e}")
        update_target_state(video_hash, target_key, "FAILED", details={"error": str(e)})
        raise RuntimeError(f"Pipeline halted because {target_key} failed to upload: {e}")

    print("\n" + "=" * 60)
    print(f"PUBLISHING REPORT SUMMARY (SUCCESS for Account {target_account_num})")
    print("=" * 60)
    return report
