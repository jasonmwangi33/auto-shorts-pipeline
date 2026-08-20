import argparse
import asyncio
import json
import os
import subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from moviepy.editor import VideoClip, ImageClip, TextClip, CompositeVideoClip, AudioFileClip, ColorClip
import edge_tts

# Make sure output directory exists
os.makedirs("output", exist_ok=True)
os.makedirs("data/tts_cache", exist_ok=True)

FONT_BOLD = "Arial-Bold"

def generate_script(seed_data: dict) -> str:
    """Expands the seed into a 3-part script."""
    headline = seed_data.get("headline", "Breaking News")
    topic = seed_data.get("topic", headline)
    hook = f"Here is something you need to know about {headline}."
    body = f"The details surrounding {topic} are changing everything we thought we knew. This development is absolutely massive."
    cta = "Follow for more updates and share this video!"
    return f"{hook} {body} {cta}"

async def generate_tts_and_timings(script: str, cache_path: str):
    """Generates Edge-TTS audio and exact word boundary timestamps."""
    communicate = edge_tts.Communicate(script, "en-US-ChristopherNeural", rate="+10%")
    word_events = []
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
        elif chunk["type"] == "WordBoundary":
            start = chunk["offset"] / 1e7
            dur = chunk["duration"] / 1e7
            word_events.append({"word": chunk["text"], "start": start, "end": start + dur})
            
    with open(cache_path, "wb") as f:
        f.write(audio_data)
    return word_events

def create_gradient_frame(t, w, h):
    """Generates procedural shifting gradients."""
    x = np.linspace(0, 1, w)[None, :, None]
    y = np.linspace(0, 1, h)[:, None, None]
    
    # Mathematical color shifting over time
    r = 0.2 + 0.3 * np.sin(2 * np.pi * (x + 0.1 * t)) + 0.2 * np.cos(2 * np.pi * (y + 0.05))
    g = 0.1 + 0.3 * np.sin(2 * np.pi * (y + 0.07 * t)) + 0.2 * np.cos(2 * np.pi * (x + 0.03))
    b = 0.3 + 0.3 * np.sin(2 * np.pi * (x * 0.5 + y * 0.5 + 0.02 * t)) + 0.1 * np.cos(2 * np.pi * (y + 0.10))
    
    frame = np.stack([r, g, b], axis=2)
    frame = np.clip(frame, 0, 1)
    return (frame * 255).astype(np.uint8)

def generate_progress_bar(duration: float, w=1080, h=1920) -> VideoClip:
    """Generates an animated progress scrubber at the bottom."""
    def make_frame(t):
        frame = np.zeros((15, w, 3), dtype=np.uint8)
        progress = int(w * min(t / duration, 1.0))
        frame[:, :progress, :] = (255, 215, 0) # Gold color
        return frame
    return VideoClip(make_frame, duration=duration).set_position(("center", "bottom"))

def build_dynamic_subtitles(word_events, duration):
    """Builds popping, word-by-word text clips."""
    clips = []
    for event in word_events:
        word = event["word"]
        start = event["start"]
        end = event["end"]
        
        if start >= duration:
            break
            
        txt = TextClip(
            word, 
            fontsize=95, 
            font=FONT_BOLD, 
            color="white", 
            stroke_color="black", 
            stroke_width=5, 
            method="caption", 
            size=(900, None), 
            align="center"
        )
        
        # Pop animation logic
        def pop_scale(t):
            pop_dur = 0.15
            if t <= pop_dur:
                return 1 + 0.3 * (1 - t / pop_dur)
            return 1.0
            
        txt = txt.resize(pop_scale)
        txt = txt.set_start(start).set_duration(end - start + 0.1)
        txt = txt.set_position(("center", 0.70), relative=True)
        clips.append(txt)
    return clips

def extract_thumbnail(video_path: str, job_id: str, t=1.0):
    final = f"output/{job_id}_thumbnail.jpg"
    subprocess.run(
        ["ffmpeg", "-y", "-ss", str(t), "-i", video_path, "-frames:v", "1", "-q:v", "2", final],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    return final

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", type=str, required=True)
    parser.add_argument("--seed-file", type=str, required=True)
    args = parser.parse_args()

    # 1. Load Data
    with open(args.seed_file, "r", encoding="utf-8") as f:
        seed_data = json.load(f)
        
    headline = seed_data.get("headline", "Trending News")
    
    print("[*] Generating Script and TTS...")
    script = generate_script(seed_data)
    audio_path = f"data/tts_cache/{args.job_id}.mp3"
    word_events = asyncio.run(generate_tts_and_timings(script, audio_path))
    
    audio_clip = AudioFileClip(audio_path)
    duration = audio_clip.duration
    
    print(f"[*] Building Visuals (Duration: {duration}s)...")
    
    # 2. Generate Gradient Background
    bg_clip = VideoClip(lambda t: create_gradient_frame(t, 1080, 1920), duration=duration)
    
    # 3. Generate Progress Bar
    progress_clip = generate_progress_bar(duration)
    
    # 4. Generate Subtitles
    subtitle_clips = build_dynamic_subtitles(word_events, duration)
    
    # 5. Build 3-Second Hook
    hook_txt = TextClip(
        headline[:50] + "...", fontsize=85, font=FONT_BOLD, color="yellow", 
        stroke_color="black", stroke_width=6, method="caption", size=(950, None), align="center"
    ).on_color(size=(1000, 300), color=(0,0,0), col_opacity=0.6).set_position(("center", 0.20), relative=True).set_start(0).set_duration(3.0)
    
    # 6. Composite Everything
    print("[*] Compositing Video...")
    video = CompositeVideoClip([bg_clip, progress_clip, hook_txt] + subtitle_clips, size=(1080, 1920))
    video = video.set_audio(audio_clip)
    
    # 7. Export
    out_path = f"output/{args.job_id}_output.mp4"
    print(f"[*] Rendering {out_path}...")
    video.write_videofile(
        out_path, fps=30, codec="libx264", audio_codec="aac", 
        preset="ultrafast", threads=4, logger=None
    )
    
    # 8. Extract Metadata & Thumbnail
    extract_thumbnail(out_path, args.job_id, t=1.0)
    meta = {"title": headline[:60], "description": script, "hashtags": ["#shorts", "#trending"]}
    Path(f"output/{args.job_id}_metadata.json").write_text(json.dumps(meta))
    
    print("[+] Render Complete!")

if __name__ == "__main__":
    main()
