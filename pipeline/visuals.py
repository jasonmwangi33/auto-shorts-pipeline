import numpy as np
from PIL import Image, ImageDraw
from moviepy.editor import ImageClip, VideoClip
from typing import Tuple, List, Dict, Any

class VisualGenerator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def generate_background(self, duration: float, size: Tuple[int, int] = (1080, 1920)) -> VideoClip:
        def make_frame(t):
            w, h = size
            # FIX: Removed the extra trailing dimensions that crashed the video compiler
            x = np.linspace(0, 1, w)[None, :]
            y = np.linspace(0, 1, h)[:, None]
            
            r = 0.15 + 0.2 * np.sin(2 * np.pi * (x + 0.1 * t)) + 0.1 * np.cos(2 * np.pi * (y + 0.05))
            g = 0.05 + 0.2 * np.sin(2 * np.pi * (y + 0.07 * t)) + 0.1 * np.cos(2 * np.pi * (x + 0.03))
            b = 0.20 + 0.3 * np.sin(2 * np.pi * (x * 0.5 + y * 0.5 + 0.02 * t)) + 0.2 * np.cos(2 * np.pi * (y + 0.10))
            
            # Now perfectly stacks into a 3D array: (Height, Width, Colors)
            frame = np.stack([r, g, b], axis=2)
            return (np.clip(frame, 0, 1) * 255).astype(np.uint8)

        clip = VideoClip(make_frame, duration=duration)
        def zoom_func(t):
            return 1 + 0.10 * (t / duration)
        return clip.resize(zoom_func).crop(x_center=size[0]/2, y_center=size[1]/2, width=size[0], height=size[1])

    def generate_progress_bar(self, duration: float, size: Tuple[int, int] = (1080, 1920)) -> VideoClip:
        w, h = size
        def make_frame(t):
            frame = np.zeros((18, w, 3), dtype=np.uint8)
            progress = int(w * min(t / duration, 1.0))
            frame[:, :progress, :] = (255, 215, 0) # Gold Scrubber
            return frame
        return VideoClip(make_frame, duration=duration).set_position(("center", "bottom"))
