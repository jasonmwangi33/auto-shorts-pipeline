import os
import random
import logging
import requests
from pathlib import Path
from moviepy.editor import VideoFileClip, concatenate_videoclips

logger = logging.getLogger("visuals")

QUERIES = [
    "satisfying cooking food vertical",
    "baking cake chocolate frosting vertical",
    "asmr kitchen cooking food prep vertical",
    "cheese melting pizza food vertical",
    "chocolate dipping fruit dessert vertical"
]

def fetch_pexels_video(query: str, index: int = 0) -> str:
    api_key = os.environ.get("PEXELS_API_KEY")
    if not api_key: return None
    headers = {"Authorization": api_key}
    url = f"https://api.pexels.com/videos/search?query={query}&per_page=30&orientation=portrait"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        videos = resp.json().get("videos", [])
        if not videos: return None
        # Deterministic selection so each story gets a unique background video, not random
        video = videos[index % len(videos)]
        files = video.get("video_files", [])
        if not files: return None
        best_file = max(files, key=lambda f: f.get("width", 0) * f.get("height", 0))
        link = best_file.get("link")
        if not link: return None

        cache_dir = Path("data/bg_cache")
        cache_dir.mkdir(parents=True, exist_ok=True)
        asset_path = cache_dir / f"pexels_{video['id']}.mp4"
        if not asset_path.exists():
            vid_resp = requests.get(link, stream=True, timeout=30)
            vid_resp.raise_for_status()
            with open(asset_path, "wb") as f:
                for chunk in vid_resp.iter_content(chunk_size=8192):
                    f.write(chunk)
        return str(asset_path)
    except Exception as e:
        logger.error(f"Pexels error: {e}")
        return None

def crop_to_9_16(clip):
    w, h = clip.size
    target_aspect = 9 / 16
    current_aspect = w / h
    if current_aspect > target_aspect:
        target_w = int(h * target_aspect)
        x_center = w / 2
        clip = clip.crop(x1=x_center - target_w/2, y1=0, x2=x_center + target_w/2, y2=h)
    else:
        target_h = int(w / target_aspect)
        y_center = h / 2
        clip = clip.crop(x1=0, y1=y_center - target_h/2, x2=w, y2=y_center + target_h/2)
    return clip.resize(height=1920, width=1080)

def make_background_clip(duration: float, seed) -> VideoFileClip:
    subclips = []
    source_readers = []
    accumulated = 0.0
    story_index = seed.get("story_index", 1)
    query = QUERIES[(story_index - 1) % len(QUERIES)]

    while accumulated < duration:
        asset_path = fetch_pexels_video(query, index=story_index)
        if not asset_path:
            asset_path = fetch_pexels_video(QUERIES[0], index=story_index)
        if not asset_path:
            raise RuntimeError("No food background assets available.")

        clip = VideoFileClip(asset_path)
        if clip.duration <= 0:
            clip.close()
            continue

        # Fast 3.0x speed
        clip = clip.speedx(3.0)
        source_readers.append(clip)

        seg_dur = min(round(random.uniform(1.5, 2.8), 2), clip.duration)
        if accumulated + seg_dur > duration:
            seg_dur = duration - accumulated

        max_start = max(0.0, clip.duration - seg_dur)
        start_time = random.uniform(0.0, max_start)

        subclip = clip.subclip(start_time, start_time + seg_dur)
        subclip = crop_to_9_16(subclip)

        subclips.append(subclip)
        accumulated += seg_dur

    final_bg = concatenate_videoclips(subclips, method="compose")
    final_bg.source_readers = source_readers
    return final_bg.subclip(0, duration)

class VisualGenerator:
    def generate_background(self, duration: float, seed=None, **kwargs):
        return make_background_clip(duration, seed)
    def generate_progress_bar(self, duration: float, video_size=(1080, 1920), **kwargs):
        from moviepy.editor import ColorClip
        w, h = video_size
        return ColorClip(size=(w, 15), color=(255, 215, 0)).set_duration(duration).set_position(("center", "bottom"))
