import random, logging
from pathlib import Path
from moviepy.editor import VideoFileClip, concatenate_videoclips

logger = logging.getLogger("visuals")

def get_segmented_background_clip(theme: str, target_duration: float):
    logger.info(f"Building background for theme: {theme}")
    category_dir = Path("assets/backgrounds") / theme.lower().replace(" / ", "_").replace(" ", "_")
    assets = [str(p) for p in category_dir.glob("*.*") if p.suffix.lower() in [".mp4", ".mov"]]
    
    if not assets: raise RuntimeError(f"No assets found for {theme}")
    
    clips = []
    accumulated = 0.0
    while accumulated < target_duration:
        asset = random.choice(assets)
        clip = VideoFileClip(asset)
        try:
            if clip.duration > 0:
                seg_dur = min(round(random.uniform(3.0, 6.0), 2), clip.duration)
                start = random.uniform(0.0, clip.duration - seg_dur)
                clips.append(clip.subclip(start, start + seg_dur))
                accumulated += seg_dur
        finally:
            clip.close() # CRITICAL MEMORY FIX
            
    final_bg = concatenate_videoclips(clips, method="compose").subclip(0, target_duration)
    return final_bg
