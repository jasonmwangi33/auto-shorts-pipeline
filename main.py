import argparse
import json
import os
import subprocess
from pathlib import Path
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, AudioFileClip, CompositeAudioClip, ColorClip
from PIL import Image, ImageEnhance

# Make sure output directory exists
os.makedirs("output", exist_ok=True)

FONT_BOLD = "Arial-Bold" # Using standard system font for GitHub Actions compatibility

def shorten_headline(seed: str, max_chars=55) -> str:
    """Create a high-intrigue hook from the seed."""
    if len(seed) <= max_chars:
        return seed
    cut = seed[:max_chars]
    return cut.rsplit(" ", 1)[0] + "..."

def make_hook_overlay(seed: str, duration=3.0, size=(1080, 1920)):
    """Displays the hook as a bold text overlay for the first 3 seconds."""
    hook_text = shorten_headline(seed)
    
    txt = TextClip(
        hook_text,
        fontsize=82,
        font=FONT_BOLD,
        color="white",
        stroke_color="black",
        stroke_width=5,
        method="caption",
        size=(int(size[0] * 0.88), None),
        align="center",
    )
    
    # Background pill for readability
    txt = txt.on_color(
        size=(txt.w + 60, txt.h + 40),
        color=(0, 0, 0),
        col_opacity=0.55,
        pos=("center", "center"),
    )
    
    # Start exactly at t=0 with no fade-in (The 3-Second Rule)
    txt = txt.set_position(("center", 0.20), relative=True)
    txt = txt.set_start(0).set_duration(duration)
    return txt

def extract_keywords(seed: str, max_tags=8):
    """Derive hashtags from the seed."""
    words = [w.strip("#").lower() for w in seed.split() if len(w.strip("#")) > 3]
    general = ["Shorts", "Tech", "Education", "AI", "Facts"]
    tags = list(dict.fromkeys(general + words))[:max_tags]
    return tags

def generate_metadata(seed: str, job_id: str):
    """Exports _metadata.json with YouTube/Instagram title and description."""
    keywords = extract_keywords(seed)
    title = f"{seed[:60]} | Must Watch"
    description = f"{seed}\n\nWatch till the end!\n\n" + " ".join(f"#{kw}" for kw in keywords)
    
    meta = {
        "title": title,
        "description": description,
        "tags": keywords,
        "hook": shorten_headline(seed),
    }
    
    out_path = Path(f"output/{job_id}_metadata.json")
    out_path.write_text(json.dumps(meta, indent=2))
    print(f"[+] Metadata generated: {out_path}")
    return meta

def extract_thumbnail(video_path: str, job_id: str, t=1.0):
    """Extracts a frame at t=1.0s, crops, and enhances it for mobile feeds."""
    raw = f"output/{job_id}_thumbnail_raw.jpg"
    final = f"output/{job_id}_thumbnail.jpg"

    # Extract frame using FFmpeg
    subprocess.run(
        ["ffmpeg", "-y", "-ss", str(t), "-i", video_path, "-frames:v", "1", "-q:v", "2", raw],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    img = Image.open(raw).convert("RGB")
    target_w, target_h = 1080, 1920
    img_ratio = img.width / img.height
    target_ratio = target_w / target_h

    # Force vertical 1080x1920 center crop
    if img_ratio > target_ratio:
        new_w = int(img.height * target_ratio)
        left = (img.width - new_w) // 2
        img = img.crop((left, 0, left + new_w, img.height))
    else:
        new_h = int(img.width / target_ratio)
        top = (img.height - new_h) // 2
        img = img.crop((0, top, img.width, top + new_h))

    img = img.resize((target_w, target_h), Image.LANCZOS)

    # High contrast / sharpness for mobile feed
    img = ImageEnhance.Contrast(img).enhance(1.25)
    img = ImageEnhance.Color(img).enhance(1.15)
    
    img.save(final, quality=95)
    print(f"[+] Thumbnail generated: {final}")
    return final

def apply_ken_burns(clip, zoom_ratio=0.10):
    """Applies a slow zoom-in to the background footage."""
    duration = clip.duration
    def scale(t):
        return 1 + zoom_ratio * (t / duration)
    return clip.resize(scale)

def main():
    parser = argparse.ArgumentParser(description="Render Short Video")
    parser.add_argument("--job-id", type=str, required=True, help="Unique job identifier")
    parser.add_argument("--seed-file", type=str, required=True, help="Path to JSON seed file")
    args = parser.parse_args()

    job_id = args.job_id
    
    # 1. Load the Seed Data
    with open(args.seed_file, "r", encoding="utf-8") as f:
        seed_data = json.load(f)
    
    headline = seed_data.get("headline", "Breaking News")
    
    # Placeholder for actual background video and audio logic
    # In a fully fleshed out script, you would download/generate TTS and background here
    # For now, we create a solid color background so the pipeline doesn't crash
    duration = 10.0 
    bg_clip = ColorClip(size=(1080, 1920), color=(20, 20, 20), duration=duration)
    
    # Apply Ken Burns effect
    bg_clip = apply_ken_burns(bg_clip)
    
    # 2. Add the Hook (3-Second Rule)
    hook_clip = make_hook_overlay(headline)
    
    # 3. Composite Video
    video = CompositeVideoClip([bg_clip, hook_clip], size=(1080, 1920))
    
    # 4. Export the MP4
    out_path = f"output/{job_id}_output.mp4"
    print(f"[*] Rendering video to {out_path}...")
    
    video.write_videofile(
        out_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast", # Using ultrafast for testing
        threads=4,
        logger=None # Silence MoviePy output for cleaner logs
    )
    
    # 5. Extract Thumbnail and Metadata
    extract_thumbnail(out_path, job_id, t=1.0)
    generate_metadata(headline, job_id)
    
    print("[+] Render Complete!")

if __name__ == "__main__":
    main()
