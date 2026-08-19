import argparse
import sys
from publishers.manager import publish_qc_video

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video-path", required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--qc-passed", action="store_true")
    parser.add_argument("--title", default="Daily Insight #Shorts")
    parser.add_argument("--yt-desc", default="Exploring tech and trends. #Shorts")
    parser.add_argument("--ig-caption", default="Daily update #reels #tech")
    parser.add_argument("--public-url", default=None)

    args = parser.parse_args()

    if not args.qc_passed:
        print("ERROR: --qc-passed flag is mandatory for publishing.", file=sys.stderr)
        sys.exit(1)

    report = publish_qc_video(
        video_path=args.video_path,
        job_id=args.job_id,
        qc_passed=args.qc_passed,
        title=args.title,
        youtube_description=args.yt_desc,
        instagram_caption=args.ig_caption,
        video_public_url=args.public_url
    )

    has_failures = any("FAILED" in status for status in report["targets"].values())
    if has_failures:
        print("Warning: One or more publishing targets failed.", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()
