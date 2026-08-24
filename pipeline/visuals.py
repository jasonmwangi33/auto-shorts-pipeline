#!/usr/bin/env python3
"""
Visuals Module: Enforces category continuity, centralized slug normalization, 
duration validation, explicit clip cleanup (.close()), and MoviePy background integration.
"""

import random
import logging
from pathlib import Path
from typing import List
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

def category_slug(theme: str) -> str:
    return theme.lower().replace(" / ", "_").replace(" ", "_")

def select_visual_theme() -> str:
    theme = random.choice(APPROVED_CATEGORIES)
    logger.info("Selected visual theme for video: %s", theme)
    return theme

def fetch_category_asset(theme: str) -> str:
    slug = category_slug(theme)
    category_dir = Path("assets") / "backgrounds" / slug
    
    if category_dir.exists():
        media_files = [str(p) for p in category_dir.glob("*.*") if p.suffix.lower() in [".mp4", ".mov", ".mkv"]]
        if media_files:
            return random.choice(media_files)
            
    cache_dir = Path("cache") / slug
    if cache_dir.exists():
        media_files = [str(p) for p in cache_dir.glob("*.*") if p.suffix.lower() in [".mp4", ".mov", ".mkv"]]
        if media_files:
            return random.choice(media_files)
            
    return ""

def get_segmented_background_clip(theme: str, target_duration_seconds: float):
    logger.info("Building category-continuous background for theme: %s (Target: %.1fs)", theme, target_duration_seconds)
    
    subclips = []
    parent_clips = []
    accumulated_duration = 0.0
    
    try:
        while accumulated_duration < target_duration_seconds:
            segment_duration = round(random.uniform(3.0, 6.0), 2)
            asset_path = fetch_category_asset(theme)
            
            if not asset_path or not Path(asset_path).exists():
                raise RuntimeError(f"CRITICAL: No valid video assets found for category '{theme}'. Silent procedural gradient fallbacks are strictly prohibited.")
                
            clip = VideoFileClip(asset_path)
            parent_clips.append(clip)
            
            if clip.duration <= 0:
                logger.warning("Asset %s has non-positive duration; skipping.", asset_path)
                clip.close()
                continue
                
            if clip.duration < segment_duration:
                segment_duration = clip.duration
                
            max_start = max(0.0, clip.duration - segment_duration)
            start_time = random.uniform(0.0, max_start)
            subclip = clip.subclip(start_time, start_time + segment_duration)
            
            subclips.append(subclip)
            accumulated_duration += segment_duration
                
        if not subclips:
            raise RuntimeError(f"CRITICAL: Failed to assemble any subclips for category '{theme}'.")
            
        final_background = concatenate_videoclips(subclips, method="compose")
        if final_background.duration < target_duration_seconds:
            loops_needed = int(target_duration_seconds // final_background.duration) + 1
            final_background = concatenate_videoclips([final_background] * loops_needed, method="compose")
            
        return final_background.subclip(0, target_duration_seconds)
    finally:
        # Cleanup parent clips properly after subclips are concatenated
        for pc in parent_clips:
            try:
                pc.close()
            except Exception:
                pass
