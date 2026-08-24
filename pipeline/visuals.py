#!/usr/bin/env python3
import random
import logging
from pathlib import Path
from moviepy.editor import VideoFileClip, concatenate_videoclips

logger = logging.getLogger("visuals")
APPROVED_CATEGORIES = [
    "ASMR Food Preparation",
    "Fast Food / Food Assembly",
    "Smoothie & Drink Preparation",
    "Cake & Dessert Decoration",
    "Satisfying Food / Ice Cutting",
    "Minecraft Parkour / Gameplay",
    "Satisfying Industrial Machinery",
    "Kinetic Sand & Satisfying Objects"
]

class VisualGenerator:
    def __init__(self, config: dict):
        self.config = config

    def select_visual_theme(self) -> str:
        return random.choice(APPROVED_CATEGORIES)

    def fetch_category_asset(self, theme: str) -> str:
        slug = theme.lower().replace(" / ", "_").replace(" ", "_")
        for base in [Path("assets") / "backgrounds" / slug, Path("cache") / slug]:
            if base.exists():
                files = [str(p) for p in base.glob("*.*") if p.suffix.lower() in [".mp4", ".mov", ".mkv"]]
                if files: return random.choice(files)
        return ""

    def get_hypercut_background(self, target_duration_seconds: float, theme: str = "ASMR Food Preparation"):
        subclips = []
        accumulated = 0.0
        while accumulated < target_duration_seconds:
            asset_path = self.fetch_category_asset(theme)
            if not asset_path or not Path(asset_path).exists():
                raise RuntimeError(f"CRITICAL: No assets found for category '{theme}'. Procedural fallbacks prohibited.")
            clip = VideoFileClip(asset_path)
            if clip.duration <= 0: continue
            segment = round(random.uniform(3.0, 6.0), 2)
            segment = min(segment, clip.duration)
            start = random.uniform(0.0, max(0.0, clip.duration - segment))
            subclips.append(clip.subclip(start, start + segment))
            accumulated += segment
        if not subclips: raise RuntimeError(f"CRITICAL: Background assembly failed for category '{theme}'.")
        final_bg = concatenate_videoclips(subclips, method="compose")
        if final_bg.duration < target_duration_seconds:
            loops = int(target_duration_seconds // final_bg.duration) + 1
            final_bg = concatenate_videoclips([final_bg] * loops, method="compose")
        return final_bg.subclip(0, target_duration_seconds)

    def generate_progress_bar(self, duration: float):
        # Fallback or stub if progress bar relies on existing implementation
        from moviepy.editor import ColorClip
        return ColorClip(size=(1080, 15), color=(255, 255, 255)).set_duration(duration)

def select_visual_theme() -> str:
    return random.choice(APPROVED_CATEGORIES)
