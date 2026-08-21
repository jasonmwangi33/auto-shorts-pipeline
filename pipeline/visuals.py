import random
import numpy as np
from pathlib import Path
from moviepy.editor import VideoFileClip, VideoClip
from typing import Tuple, Dict, Any

class VisualGenerator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.backgrounds_dir = Path("assets/backgrounds")

    def get_background_clip(self, duration: float, size: Tuple[int, int] = (1080, 1920)) -> VideoClip:
        target_w, target_h = size
        video_extensions = ("*.mp4", "*.mov", "*.mkv", "*.webm")
        bg_files = []
        if self.backgrounds_dir.exists():
            for ext in video_extensions:
                bg_files.extend(list(self.backgrounds_dir.glob(ext)))

        if bg_files:
            chosen_video = random.choice(bg_files)
            try:
                clip = VideoFileClip(str(chosen_video), audio=False)
                if clip.duration > duration + 2.0:
                    start_t = random.uniform(0, clip.duration - duration - 1.0)
                    clip = clip.subclip(start_t, start_t + duration)
                else:
                    clip = clip.loop(duration=duration)

                # Aspect ratio crop to 9:16 vertical
                orig_w, orig_h = clip.size
                scale_factor = max(target_w / orig_w, target_h / orig_h)
                clip = clip.resize(scale_factor)
                clip = clip.crop(x_center=clip.w / 2, y_center=clip.h / 2, width=target_w, height=target_h)
                return clip
            except Exception as e:
                print(f"[-] Error loading background video {chosen_video}: {e}. Falling back to procedural motion.")

        # Procedural fallback if no videos are in assets/backgrounds
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
