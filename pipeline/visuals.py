import os
import random
import subprocess
import numpy as np
from pathlib import Path
from moviepy.editor import VideoFileClip, VideoClip
from typing import Tuple, Dict, Any

# Curated pool of high-quality, copyright-free / CC background loops
ONLINE_BACKGROUND_SOURCES = [
    # Minecraft Parkour Loops
    "https://www.youtube.com/watch?v=n_Dv4JMiwK8",
    "https://www.youtube.com/watch?v=qWbHSO_4x4U",
    # ASMR Cooking & Satisfying Food Prep
    "https://www.youtube.com/watch?v=7X8II6J-6mU",
    # Satisfying Kinetic Cutting / Sand
    "https://www.youtube.com/watch?v=gX_Qy3rLw8w"
]

class VisualGenerator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.cache_dir = Path("data/bg_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch_online_background(self, target_duration: float) -> Optional[Path]:
        """Downloads a fast 60s section of satisfying footage directly on the cloud runner."""
        chosen_source = random.choice(ONLINE_BACKGROUND_SOURCES)
        cache_id = f"bg_{abs(hash(chosen_source)) % 10000}"
        out_file = self.cache_dir / f"{cache_id}.mp4"

        if out_file.exists() and out_file.stat().st_size > 100000:
            return out_file

        print(f"[*] Fetching satisfying online footage slice from: {chosen_source}")
        start_sec = random.choice([30, 60, 120, 180])
        end_sec = start_sec + int(target_duration) + 15
        section_str = f"*{start_sec:02d}:00-{end_sec:02d}:00"

        cmd = [
            "yt-dlp",
            "--no-check-certificates",
            "--download-sections", f"*{start_sec}-{end_sec}",
            "-f", "bestvideo[height<=1080][ext=mp4]/best[height<=1080]",
            "-o", str(out_file),
            chosen_source
        ]

        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=90, check=True)
            if out_file.exists() and out_file.stat().st_size > 100000:
                return out_file
        except Exception as e:
            print(f"[-] yt-dlp download failed ({e}). Trying fallback...")

        return None

    def get_background_clip(self, duration: float, size: Tuple[int, int] = (1080, 1920)) -> VideoClip:
        target_w, target_h = size
        
        # 1. Check local assets/backgrounds folder first if user provided any
        local_dir = Path("assets/backgrounds")
        bg_files = []
        if local_dir.exists():
            for ext in ("*.mp4", "*.mov", "*.mkv", "*.webm"):
                bg_files.extend(list(local_dir.glob(ext)))

        bg_path = random.choice(bg_files) if bg_files else self.fetch_online_background(duration)

        if bg_path and Path(bg_path).exists():
            try:
                clip = VideoFileClip(str(bg_path), audio=False)
                if clip.duration > duration + 1.0:
                    start_t = random.uniform(0, max(0.1, clip.duration - duration - 0.5))
                    clip = clip.subclip(start_t, start_t + duration)
                else:
                    clip = clip.loop(duration=duration)

                # Center-crop to 9:16 vertical ratio
                orig_w, orig_h = clip.size
                scale_factor = max(target_w / orig_w, target_h / orig_h)
                clip = clip.resize(scale_factor)
                clip = clip.crop(x_center=clip.w / 2, y_center=clip.h / 2, width=target_w, height=target_h)
                return clip
            except Exception as e:
                print(f"[-] Error processing background clip: {e}. Falling back to smooth motion.")

        # Procedural fallback if offline / network throttled
        def make_frame(t):
            x = np.linspace(0, 1, target_w)[None, :]
            y = np.linspace(0, 1, target_h)[:, None]
            r = 0.12 + 0.15 * np.sin(2 * np.pi * (x + 0.08 * t)) + 0.08 * np.cos(2 * np.pi * (y + 0.04))
            g = 0.06 + 0.15 * np.sin(2 * np.pi * (y + 0.05 * t)) + 0.08 * np.cos(2 * np.pi * (x + 0.02))
            b = 0.22 + 0.20 * np.sin(2 * np.pi * (x * 0.5 + y * 0.5 + 0.03 * t))
            frame = np.stack([r, g, b], axis=2)
            return (np.clip(frame, 0, 1) * 255).astype(np.uint8)

        base = VideoClip(make_frame, duration=duration)
        return base.resize(lambda t: 1 + 0.08 * (t / duration)).crop(x_center=target_w / 2, y_center=target_h / 2, width=target_w, height=target_h)

    def generate_progress_bar(self, duration: float, size: Tuple[int, int] = (1080, 1920)) -> VideoClip:
        w, h = size
        def make_frame(t):
            frame = np.zeros((16, w, 3), dtype=np.uint8)
            progress = int(w * min(t / duration, 1.0))
            frame[:, :progress, :] = (255, 215, 0)
            return frame
        return VideoClip(make_frame, duration=duration).set_position(("center", "bottom"))
