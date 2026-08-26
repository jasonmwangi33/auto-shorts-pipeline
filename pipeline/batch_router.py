import os
import sys
import json
import time
import random
import requests
import asyncio
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
        return raw_text, "Crazy Reddit Story You Won't Believe #shorts"
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    story_prompt = f"""
    Rewrite the following story into a fast-paced, high-retention first-person short story.
    Keep it engaging and optimized for vertical video. Do not add moral advice.
    Raw Story: {raw_text}
    """
    title_prompt = f"""
    Create a catchy, viral YouTube Short title (under 50 characters) with emojis and hashtags based on this story:
    {raw_text}
    """
    try:
        story_res = model.generate_content(story_prompt).text.strip()
        title_res = model.generate_content(title_prompt).text.strip()
        return story_res, title_res
    except Exception as e:
        print(f"[!] Gemini Error: {e}")
        return raw_text, "Crazy Reddit Story #shorts"

def split_story(text):
    words = text.split()
    max_single_video_words = 200
    min_part2_words = 120

    if len(words) <= max_single_video_words:
        return [(text, "")]
    
    mid = len(words) // 2
    part1_words = words[:mid]
    part2_words = words[mid:]

    if len(part2_words) < min_part2_words:
        return [(text, "")]
    else:
        return [
            (" ".join(part1_words), "Part 1"),
            (" ".join(part2_words), "Part 2")
        ]

async def generate_tts(text, output_path):
    import edge_tts
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
    titles = {}
    for i in range(1, 8):
        story = os.getenv(f"STORY_{i}")
        if story and len(story.strip()) > 0:
            print(f"[*] AI Processing Story {i}...")
            polished, custom_title = polish_story_with_gemini(story)
            processed[str(i)] = split_story(polished)
            titles[str(i)] = custom_title
            time.sleep(1)

    if not processed:
        print("[-] No stories provided. Stopping pipeline.")
        sys.exit(0)

    with open(AI_DATA_FILE, "w") as f:
        json.dump({"stories": processed, "titles": titles}, f)
    print("[+] AI processing & unique title generation complete.")

def run_stage_2():
    print("[*] PROCESS 2: Local Rendering Engine (Batch Processing All Stories)")
    if not os.path.exists(AI_DATA_FILE):
        raise FileNotFoundError("CRITICAL FAIL: AI data missing. Stage 1 must complete first.")

    with open(AI_DATA_FILE, "r") as f:
        data = json.load(f)
        processed = data.get("stories", {})

    if not processed:
        print("[-] No stories found to render.")
        return

    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from pipeline.renderer import Renderer
    renderer = Renderer()

    renders = {}
    if os.path.exists(RENDER_DATA_FILE):
        try:
            with open(RENDER_DATA_FILE, "r") as f:
                renders = json.load(f)
        except: pass

    for story_key, chunks in processed.items():
        print(f"[*] Rendering Story {story_key}...")
        renders[story_key] = []
        for idx, (text, part_title) in enumerate(chunks):
            formatted_title = part_title.upper() if part_title else f"PART {idx+1}"
            job_id = f"story_{story_key}_part_{idx+1}"
            audio_path = os.path.join(WORKSPACE_DIR, f"{job_id}.mp3")
            video_path = os.path.join(WORKSPACE_DIR, f"{job_id}.mp4")

            print(f"[*] Generating Fast AI Voiceover for Story {story_key} {formatted_title}...")
            word_events = asyncio.run(generate_tts(text, audio_path))

            print(f"[*] Compositing Food Background Video for Story {story_key} {formatted_title}...")
            seed = {
                "id": job_id,
                "script": text,
                "audio_path": audio_path,
                "word_timings": word_events,
                "story_index": int(story_key)
            }

            try:
                result = renderer.render_short(seed, video_path)
                print(f"[+] Render Finished: {result.video_path}")
                renders[story_key].append(result.video_path)
            except Exception as e:
                raise RuntimeError(f"CRITICAL FAIL: Renderer crashed on {job_id}. Error: {e}")

    with open(RENDER_DATA_FILE, "w") as f:
        json.dump(renders, f)
    print("[+] All story parts successfully rendered.")

def run_stage_3():
    print("[*] PROCESS 3: Strict 1-to-1 Account-Isolated Publishing")
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    try:
        from publishers.manager import publish_qc_video
    except ImportError:
        raise ImportError("CRITICAL FAIL: Publishers manager could not be imported.")

    all_renders = {}
    workspace_all = "workspace_all"
    if os.path.exists(workspace_all):
        for root, dirs, files in os.walk(workspace_all):
            if "render_output.json" in files:
                try:
                    with open(os.path.join(root, "render_output.json"), "r") as f:
                        data = json.load(f)
                        for k, v in data.items():
                            if k not in all_renders: all_renders[k] = []
                            all_renders[k].extend(v)
                except: pass

    if not all_renders and os.path.exists(RENDER_DATA_FILE):
        with open(RENDER_DATA_FILE, "r") as f:
            all_renders = json.load(f)

    if not all_renders:
        raise RuntimeError("CRITICAL FAIL: No local render outputs found. Cannot publish.")

    titles = {}
    if os.path.exists(AI_DATA_FILE):
        try:
            with open(AI_DATA_FILE, "r") as f:
                d = json.load(f)
                titles = d.get("titles", {})
        except: pass

    accounts = []
    try:
        acc_env = os.getenv("YOUTUBE_ACCOUNTS_JSON")
        if acc_env:
            accounts = json.loads(acc_env)
    except: pass

    for index, video_paths in all_renders.items():
        story_idx = int(index)
        
        if accounts and len(accounts) > 0:
            target_account_index = (story_idx - 1) % len(accounts)
        else:
            target_account_index = 0

        custom_title = titles.get(str(story_idx), f"Satisfying Story #{story_idx} #shorts")

        for idx, local_video_path in enumerate(video_paths):
            if not os.path.exists(local_video_path):
                raise RuntimeError(f"CRITICAL FAIL: Video file missing at {local_video_path}")

            video_title = f"{custom_title} (Part {idx+1})" if len(video_paths) > 1 else custom_title
            desc_text = "What would you do in this situation? Comment below! #shorts #reddit #storytime"

            print(f"[FORCE] Publishing Story {story_idx} EXCLUSIVELY to YouTube Account #{target_account_index + 1}...")

            try:
                publish_qc_video(
                    video_path=local_video_path,
                    job_id=f"story_{index}_part_{idx+1}",
                    qc_provenance_index=target_account_index,
                    qc_passed=True,
                    title=video_title,
                    youtube_description=desc_text,
                    instagram_caption=desc_text,
                    video_public_url=""
                )
                print(f"[+] Success: Story {story_idx} locked and published to Account #{target_account_index + 1}.")
            except Exception as e:
                raise RuntimeError(f"CRITICAL FAIL: Strict account isolation failed on Story {story_idx} for Account #{target_account_index + 1}. Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(1)
    stage = sys.argv[1]
    if stage == "1": run_stage_1()
    elif stage == "2": run_stage_2()
    elif stage == "3": run_stage_3()
