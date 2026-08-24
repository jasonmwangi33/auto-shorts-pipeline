import os
import random
import requests
import numpy as np
from pathlib import Path
from moviepy.editor import VideoFileClip, VideoClip, concatenate_videoclips
from typing import Tuple, Dict, Any, List

class BackgroundProvider:
    def get_clips(self, theme: str, count: int) -> List[str]:
        raise NotImplementedError

class PexelsBackgroundProvider(BackgroundProvider):
    def __init__(self):
        self.api_key = os.environ.get("PEXELS_API_KEY", "")
        self.cache_dir = Path("data/bg_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_clips(self, theme: str, count: int) -> List[str]:
        if not self.api_key:
            print("[-] PEXELS_API_KEY not found. Skipping Pexels provider.")
            return []
            
        print(f"[*] Fetching '{theme}' footage from Pexels API...")
        headers = {"Authorization": self.api_key}
        url = f"https://api.pexels.com/videos/search?query={theme}&orientation=portrait&size=medium&per_page=15"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            downloaded = []
            for video in data.get("videos", [])[:count]:
                files = video.get("video_files", [])
                if not files: continue
                
                # Grab a solid mp4 link
                link = next((f["link"] for f in files if f["file_type"] == "video/mp4"), files[0]["link"])
                video_id = video["id"]
                out_path = self.cache_dir / f"pexels_{video_id}.mp4"
                
                if not out_path.exists():
                    vid_resp = requests.get(link, stream=True, timeout=15)
                    with open(out_path, 'wb') as f:
                        for chunk in vid_resp.iter_content(chunk_size=8192):
                            f.write(chunk)
                downloaded.append(str(out_path))
            return downloaded
        except Exception as e:
            print(f"[-] Pexels API failure: {e}")
            return []

class PreloadedBackgroundProvider(BackgroundProvider):
    def __init__(self):
        self.local_dir = Path("assets/backgrounds")

    def get_clips(self, theme: str, count: int) -> List[str]:
        if not self.local_dir.exists():
            return []
        files = []
        for ext in ("*.mp4", "*.mov"):
            files.extend([str(p) for p in self.local_dir.glob(ext)])
        random.shuffle(files)
        return files[:count]

class VisualGenerator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.providers = [PexelsBackgroundProvider(), PreloadedBackgroundProvider()]

    def get_hypercut_background(self, duration: float, theme: str, size: Tuple[int, int] = (1080, 1920)) -> VideoClip:
        target_w, target_h = size
        raw_clips = []
        
        # Try providers in order
        for provider in self.providers:
            raw_clips = provider.get_clips(theme, count=10)
            if len(raw_clips) > 0:
                break
                
        if not raw_clips:
            # Loud failure instead of silent gradient fallback
            raise RuntimeError(f"CRITICAL FAILURE: No background footage could be sourced for theme '{theme}'. Render aborted.")

        assembled_clips = []
        current_dur = 0.0
        last_clip = None

        print(f"[*] Assembling hyper-cut background ({duration}s target)")
        
        # Hyper-cut assembly loop (2 to 4 second cuts)
        while current_dur < duration:
            available = [c for c in raw_clips if c != last_clip]
            if not available:
                available = raw_clips # Fallback if only 1 clip exists
                
            chosen_file = random.choice(available)
            last_clip = chosen_file
            
            try:
                clip = VideoFileClip(chosen_file, audio=False)
                cut_length = random.uniform(2.0, 4.0)
                
                # Ensure we don't request more time than the clip has
                if clip.duration <= cut_length:
                    segment = clip
                else:
                    start_t = random.uniform(0, clip.duration - cut_length)
                    segment = clip.subclip(start_t, start_t + cut_length)
                
                # Apply vertical math
                orig_w, orig_h = segment.size
                scale_factor = max(target_w / orig_w, target_h / orig_h)
                segment = segment.resize(scale_factor)
                segment = segment.crop(x_center=segment.w / 2, y_center=segment.h / 2, width=target_w, height=target_h)
                
                assembled_clips.append(segment)
                current_dur += segment.duration
            except Exception as e:
                print(f"[-] Dropping corrupted clip {chosen_file}: {e}")
                raw_clips.remove(chosen_file)
                if not raw_clips:
                     raise RuntimeError("CRITICAL FAILURE: All sourced clips were corrupted.")
        
        final_bg = concatenate_videoclips(assembled_clips, method="compose")
        return final_bg.set_duration(duration)

    def generate_progress_bar(self, duration: float, size: Tuple[int, int] = (1080, 1920)) -> VideoClip:
        w, h = size
        def make_frame(t):
            frame = np.zeros((16, w, 3), dtype=np.uint8)
            progress = int(w * min(t / duration, 1.0))
            frame[:, :progress, :] = (255, 215, 0)
            return frame
        return VideoClip(make_frame, duration=duration).set_position(("center", "bottom"))
