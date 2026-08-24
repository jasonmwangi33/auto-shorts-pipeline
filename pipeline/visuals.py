#!/usr/init/env python3
import random
import logging
import os
from pathlib import Path
from moviepy.editor import VideoFileClip, concatenate_videoclips, ColorClip

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
        # Safe environment check for background video API keys if configured
        self.video_api_key = os.getenv("PEXELS_API_KEY") or os.getenv("VIDEO_API_KEY")

    def select_visual_theme(self) -> str:
        return random.choice(APPROVED_CATEGORIES)

    def fetch_category_asset(self, theme: str) -> str:
        slug = theme.lower().replace(" / ", "_").replace(" ", "_")
        for base in [Path("assets") / "backgrounds" / slug, Path("cache") / slug]:
            if base.exists():
                files = [str(p) for p in base.glob("*.*") if p.suffix.lower() in [".mp4", ".mov", ".mkv"]]
                if files: return random.choice(files)
        
        fallback_root = Path("assets") / "backgrounds"
        if fallback_root.exists():
            all_files = [str(p) for p in fallback_root.glob("**/*.*") if p.suffix.lower() in [".mp4", ".mov", ".mkv"]]
            if all_files:
                return random.choice(all_files)
        return ""

    def get_hypercut_background(self, target_duration_seconds: float, theme: str = "ASMR Food Preparation"):
        subclips = []
        accumulated = 0.0
        while accumulated < target_duration_seconds:
            asset_path = self.fetch_category_asset(theme)
            if not asset_path or not Path(asset_path).exists():
                return ColorClip(size=(1080, 1920), color=(20, 20, 20)).set_duration(target_duration_seconds)
                
            clip = VideoFileClip(asset_path)
            if clip.duration <= 0: continue
            segment = round(random.uniform(3.0, 6.0), 2)
            segment = min(segment, clip.duration)
            start = random.uniform(0.0, max(0.0, clip.duration - segment))
            subclips.append(clip.subclip(start, start + segment))
            accumulated += segment
            
        if not subclips: 
            return ColorClip(size=(1080, 1920), color=(20, 20, 20)).set_duration(target_duration_seconds)
            
        final_bg = concatenate_videoclips(subclips, method="compose")
        if final_bg.duration < target_duration_seconds:
            loops = int(target_duration_seconds // final_bg.duration) + 1
            final_bg = concatenate_videoclips([final_bg] * loops, method="compose")
        return final_bg.subclip(0, target_duration_seconds)

    def generate_progress_bar(self, duration: float):
        return ColorClip(size=(1080, 15), color=(255, 255, 255)).set_duration(duration)

def select_visual_theme() -> str:
    return random.choice(APPROVED_CATEGORIES)
