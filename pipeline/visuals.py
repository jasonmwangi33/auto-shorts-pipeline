import os
import random
import logging
import requests
from pathlib import Path
from moviepy.editor import VideoFileClip, concatenate_videoclips

logger = logging.getLogger("visuals")

# Strict visual vocabulary registry
VISUAL_REGISTRY = {
    "food": {
        "keywords": ["cooking", "food", "restaurant", "baking", "recipe", "eat", "taste", "chef", "kitchen", "meal"],
        "queries": ["satisfying food preparation", "street food assembly", "cake decorating", "cooking close up"],
        "local_dir": "assets/backgrounds/food",
        "pexels_enabled": True
    },
    "gaming": {
        "keywords": ["minecraft", "gaming", "parkour", "game", "gameplay", "player"],
        "queries": ["minecraft parkour", "minecraft gameplay"],
        "local_dir": "assets/backgrounds/gaming",
        "pexels_enabled": False
    },
    "asmr": {
        "keywords": ["satisfying", "cutting", "sand", "machinery", "factory", "process", "smooth"],
        "queries": ["kinetic sand", "satisfying machinery", "hydraulic press"],
        "local_dir": "assets/backgrounds/asmr",
        "pexels_enabled": True
    },
    "lifestyle": {
        "keywords": ["city", "walking", "psychology", "life", "human", "behavior", "urban", "street"],
        "queries": ["city walking", "urban lifestyle", "people walking city"],
        "local_dir": "assets/backgrounds/lifestyle",
        "pexels_enabled": True
    }
}

def semantic_router(story_text: str) -> str:
    """Routes the story to an approved category based on keyword density."""
    if not story_text:
        return "gaming"
    
    text_lower = story_text.lower()
    for category, data in VISUAL_REGISTRY.items():
        for keyword in data["keywords"]:
            if keyword in text_lower:
                logger.info(f"Semantic match found: '{keyword}' -> {category}")
                return category
                
    logger.info("No semantic match found. Defaulting to gaming.")
    return "gaming"

def fetch_pexels_video(query: str) -> str:
    """Fetches high-quality vertical footage via Pexels API."""
    api_key = os.environ.get("PEXELS_API_KEY")
    if not api_key:
        logger.warning("PEXELS_API_KEY not found in environment.")
        return None
    
    headers = {"Authorization": api_key}
    url = f"https://api.pexels.com/videos/search?query={query}&per_page=15&orientation=portrait"
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        videos = data.get("videos", [])
        if not videos:
            return None
            
        video = random.choice(videos)
        files = video.get("video_files", [])
        if not files:
            return None
            
        # Select best available resolution
        best_file = max(files, key=lambda f: f.get("width", 0) * f.get("height", 0))
        download_link = best_file.get("link")
        
        if not download_link:
            return None
            
        cache_dir = Path("data/bg_cache")
        cache_dir.mkdir(parents=True, exist_ok=True)
        asset_path = cache_dir / f"pexels_{video['id']}.mp4"
        
        # Download if not cached
        if not asset_path.exists():
            logger.info(f"Downloading Pexels asset to {asset_path}")
            vid_resp = requests.get(download_link, stream=True, timeout=30)
            vid_resp.raise_for_status()
            with open(asset_path, "wb") as f:
                for chunk in vid_resp.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
        return str(asset_path)
        
    except Exception as e:
        logger.error(f"Pexels API error for query '{query}': {e}")
        return None

def get_local_asset(category: str) -> str:
    """Gets a guaranteed category-correct fallback asset from the local directory."""
    local_dir = Path(VISUAL_REGISTRY[category]["local_dir"])
    if not local_dir.exists():
        return None
    assets = [str(p) for p in local_dir.glob("*.*") if p.suffix.lower() in [".mp4", ".mov"]]
    if not assets:
        return None
    return random.choice(assets)

def crop_to_9_16(clip):
    """Performs a mathematical center-weighted crop to 9:16 mobile ratio."""
    w, h = clip.size
    target_aspect = 9 / 16
    current_aspect = w / h
    
    if current_aspect > target_aspect:
        # Video is wider than 9:16; crop sides
        target_w = int(h * target_aspect)
        x_center = w / 2
        clip = clip.crop(x1=x_center - target_w/2, y1=0, x2=x_center + target_w/2, y2=h)
    else:
        # Video is taller than 9:16; crop top/bottom
        target_h = int(w / target_aspect)
        y_center = h / 2
        clip = clip.crop(x1=0, y1=y_center - target_h/2, x2=w, y2=y_center + target_h/2)
        
    return clip.resize(height=1920, width=1080)

def make_background_clip(duration: float, seed) -> VideoFileClip:
    """
    Constructs a category-continuous, 9:16, fast-cut background.
    Returns the MoviePy composite object. Retains reader references internally 
    for lazy evaluation in the final render.
    """
    logger.info(f"Generating semantic background for duration {duration}s")
    
    story_text = ""
    if isinstance(seed, dict):
        story_text = seed.get("script", seed.get("story", seed.get("text", "")))
    elif isinstance(seed, str):
        story_text = seed
        
    category = semantic_router(story_text)
    registry = VISUAL_REGISTRY[category]
    
    subclips = []
    source_readers = [] # Retain references so MoviePy readers stay alive during render
    accumulated = 0.0
    
    try:
        while accumulated < duration:
            asset_path = None
            
            if registry["pexels_enabled"]:
                query = random.choice(registry["queries"])
                asset_path = fetch_pexels_video(query)
            
            # Semantic Local Fallback
            if not asset_path:
                asset_path = get_local_asset(category)
                
            # Strict Hard Failure Rule (No generic gradients)
            if not asset_path:
                raise RuntimeError(f"CRITICAL: No assets available for assigned category '{category}'. Semantic continuity enforced; failing job.")
                
            clip = VideoFileClip(asset_path)
            if clip.duration <= 0:
                clip.close()
                continue
                
            # Bind the reader
            source_readers.append(clip)
            
            # 3 to 6-second fast cuts
            seg_dur = min(round(random.uniform(3.0, 6.0), 2), clip.duration)
            if accumulated + seg_dur > duration:
                seg_dur = duration - accumulated
                
            max_start = max(0.0, clip.duration - seg_dur)
            start_time = random.uniform(0.0, max_start)
            
            subclip = clip.subclip(start_time, start_time + seg_dur)
            subclip = crop_to_9_16(subclip)
            
            subclips.append(subclip)
            accumulated += seg_dur
            
        final_bg = concatenate_videoclips(subclips, method="compose")
        
        # Attach the readers to the composite clip so they are not garbage collected
        # until the renderer finishes and destroys the composite clip.
        final_bg.source_readers = source_readers 
        
        return final_bg.subclip(0, duration)
        
    except Exception as e:
        # Explicit cleanup if assembly crashes halfway
        logger.error(f"Failed during background composition: {e}")
        for reader in source_readers:
            try: reader.close()
            except: pass
        for sc in subclips:
            try: sc.close()
            except: pass
        raise


def select_visual_theme() -> str:
    return 'gaming'

