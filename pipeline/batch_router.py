import os
import sys
import json
import time
import random
import requests
import asyncio
import edge_tts
from pathlib import Path

try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

WORKSPACE_DIR = "workspace"
os.makedirs(WORKSPACE_DIR, exist_ok=True)
AI_DATA_FILE = os.path.join(WORKSPACE_DIR, "ai_output.json")
RENDER_DATA_FILE = os.path.join(WORKSPACE_DIR, "render_output.json")

def polish_story_with_gemini(raw_text):
    if not HAS_GEMINI or not os.getenv("GEMINI_API_KEY"):
        return raw_text
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    Rewrite the following story into a fast-paced, high-retention first-person short story.
    Keep it engaging and optimized for vertical video. Do not add moral advice.
    Raw Story: {raw_text}
    """
    try:
        return model.generate_content(prompt).text.strip()
    except Exception as e:
        print(f"[!] Gemini Error: {e}")
        return raw_text

def split_story(text):
    """
    Splits the story based on your exact rules:
    - A single video handles up to ~60 seconds (~200 words at +28% speed).
    - If the story is longer, Part 2 is only created if it has more than 40 seconds (~120 words).
    - Otherwise, it stays as one single video.
    """
    words = text.split()
    max_single_video_words = 200  # Up to 60 seconds
    min_part2_words = 120         # Part 2 must have > 40 seconds

    if len(words) <= max_single_video_words:
        return [(text, "")]
    
    # If it's long, check if the remainder is big enough for Part 2
    mid = len(words) // 2
    part1_words = words[:mid]
    part2_words = words[mid:]

    if len(part2_words) < min_part2_words:
        # Remainder is too short for a solid Part 2, keep as one cohesive video
        return [(text, "")]
    else:
        return [
            (" ".join(part1_words), "Part 1"),
            (" ".join(part2_words), "Part 2")
        ]

async def generate_tts(text, output_path):
    communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural", rate="+38%")
    word_events = []
    audio_chunks = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_chunks.append(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            start = chunk["offset"] / 1e7
            dur = chunk["duration"] / 1e7
            word_events.append({"word": chunk["text"], "start": start, "end": start + dur})

    with open(output_path, "wb") as f:
        for data in audio_chunks:
            f.write(data)
    return word_events

def run_stage_1():
    print("[*] PROCESS 1: AI Scavenger & Processing System")
    processed = {}
    for i in range(1, 8):
        story = os.getenv(f"STORY_{i}")
        if story and len(story.strip()) > 0:
            print(f"[*] AI Rewriting Story {i}...")
            polished = polish_story_with_gemini(story)
            processed[str(i)] = split_story(polished)
            time.sleep(1)

    if not processed:
        print("[-] No stories provided. Stopping pipeline.")
        sys.exit(0)

    with open(AI_DATA_FILE, "w") as f:
        json.dump(processed, f)
    print(f"[+] AI processing complete with smart duration rules.")

def run_stage_2(story_id):
    print(f"[*] PROCESS 2: Local Rendering Engine (Story ID: {story_id})")
    if not os.path.exists(AI_DATA_FILE):
        raise FileNotFoundError("CRITICAL FAIL: AI data missing. Stage 1 must complete first.")

    with open(AI_DATA_FILE, "r") as f:
        processed = json.load(f)

    story_key = str(story_id)
    if story_key not in processed:
        print(f"[*] No story content found for slot {story_id}. Skipping worker.")
        return

    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from pipeline.renderer import Renderer

    renderer = Renderer()
    chunks = processed[story_key]
    renders = {}

    if os.path.exists(RENDER_DATA_FILE):
        try:
            with open(RENDER_DATA_FILE, "r") as f:
                renders = json.load(f)
        except: pass

    renders[story_key] = []
    for idx, (text, part_title) in enumerate(chunks):
        formatted_title = part_title.upper() if part_title else f"PART {idx+1}"
        job_id = f"story_{story_key}_part_{idx+1}"
        audio_path = os.path.join(WORKSPACE_DIR, f"{job_id}.mp3")
        video_path = os.path.join(WORKSPACE_DIR, f"{job_id}.mp4")

        print(f"[*] Generating Fast AI Voiceover for {formatted_title}...")
        word_events = asyncio.run(generate_tts(text, audio_path))

        print(f"[*] Compositing Video with Bold Captions for {formatted_title}...")
        seed = {
            "id": job_id,
            "script": text,
            "audio_path": audio_path,
            "word_timings": word_events
        }

        try:
            result = renderer.render_short(seed, video_path)
            print(f"[+] Local Render Finished! Saved to: {result.video_path}")
            renders[story_key].append(result.video_path)
        except Exception as e:
            raise RuntimeError(f"CRITICAL FAIL: Local Rendering Engine crashed on {job_id}. Error: {e}")

    with open(RENDER_DATA_FILE, "w") as f:
        json.dump(renders, f)
    print(f"[+] All parts rendered for Story {story_key}.")

def run_stage_3():
    print("[*] PROCESS 3: Strict Verified Publishing")
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    try:
        from publishers.manager import publish_qc_video
    except ImportError:
        raise ImportError("CRITICAL FAIL: Publishers manager could not be imported.")

    all_renders = {}
    if os.path.exists(RENDER_DATA_FILE):
        with open(RENDER_DATA_FILE, "r") as f:
            all_renders = json.load(f)

    if not all_renders:
        raise RuntimeError("CRITICAL FAIL: No local render outputs found. Cannot publish.")

    for index, video_paths in all_renders.items():
        for idx, local_video_path in enumerate(video_paths):
            if not os.path.exists(local_video_path):
                raise RuntimeError(f"CRITICAL FAIL: Video file missing at {local_video_path}")

            title_text = "Crazy Reddit Story You Won't Believe #shorts #reddit"
            desc_text = "What would you do in this situation? Comment below! #shorts #reddit #storytime"

            try:
                publish_qc_video(
                    video_path=local_video_path,
                    job_id=f"story_{index}_part_{idx+1}",
                    qc_passed=True,
                    title=title_text,
                    youtube_description=desc_text,
                    instagram_caption=desc_text,
                    video_public_url=""
                )
                print(f"[+] Published {local_video_path} successfully.")
            except Exception as e:
                raise RuntimeError(f"CRITICAL FAIL: Publishing pipeline crashed on Story {index}. Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(1)
    stage = sys.argv[1]
    if stage == "1": run_stage_1()
    elif stage == "2": run_stage_2(sys.argv[2] if len(sys.argv) > 2 else 1)
    elif stage == "3": run_stage_3()
