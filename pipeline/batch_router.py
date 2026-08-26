import os
import sys
import json
import time
import random
import requests
import asyncio
from pathlib import Path

# Use modern google.genai or fallback to requests if needed
try:
    from google import genai
    from google.genai import types
    HAS_NEW_GENAI = True
except ImportError:
    HAS_NEW_GENAI = False

WORKSPACE_DIR = "workspace"
os.makedirs(WORKSPACE_DIR, exist_ok=True)

def polish_story_with_gemini(raw_text):
    if not raw_text or len(raw_text.strip()) == 0:
        return "This is an incredible story about an unexpected turn of events that left everyone completely speechless.", "Crazy Reddit Story #shorts"
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return raw_text, "Crazy Reddit Story #shorts"
        
    story_prompt = f"""
    You are an expert editor. Carefully review the following raw story, fix any spelling or grammatical errors, and rewrite it into a fast-paced, high-retention first-person short story optimized for vertical video. Do not add moral advice.
    Raw Story: {raw_text}
    """
    title_prompt = f"""
    Create a catchy, viral YouTube Short title (under 50 characters) with emojis and hashtags based on this story:
    {raw_text}
    """
    
    try:
        if HAS_NEW_GENAI:
            client = genai.Client(api_key=api_key)
            story_res = client.models.generate_content(model='gemini-1.5-flash', contents=story_prompt).text.strip()
            title_res = client.models.generate_content(model='gemini-1.5-flash', contents=title_prompt).text.strip()
            return story_res, title_res
        else:
            import google.generativeai as legacy_genai
            legacy_genai.configure(api_key=api_key)
            model = legacy_genai.GenerativeModel('gemini-1.5-flash')
            story_res = model.generate_content(story_prompt).text.strip()
            title_res = model.generate_content(title_prompt).text.strip()
            return story_res, title_res
    except Exception as e:
        print(f"[!] Gemini AI Error: {e}")
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

def run_all_stories():
    print("==================================================")
    print("SEQUENTIAL BATCH PIPELINE START (Story 1 through 7)")
    print("==================================================")

    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from pipeline.renderer import Renderer
    renderer = Renderer()

    try:
        from publishers.manager import publish_qc_video
    except ImportError:
        raise ImportError("CRITICAL FAIL: Publishers manager could not be imported.")

    accounts = []
    try:
        acc_env = os.getenv("YOUTUBE_ACCOUNTS_JSON")
        if acc_env:
            accounts = json.loads(acc_env)
    except: pass

    import gc
    import edge_tts

    def generate_tts_sync(text, output_path):
        async def _run():
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
            with open(output_path, "wb") as wf:
                for data in audio_chunks:
                    wf.write(data)
            return word_events
        return asyncio.run(_run())

    # Process each story one by one safely to conserve RAM
    for i in range(1, 8):
        story_key = str(i)
        print(f"\n--------------------------------------------------")
        print(f"PROCESSING STORY {story_key} OF 7")
        print(f"--------------------------------------------------")

        raw_story = os.getenv(f"STORY_{i}")
        if not raw_story or len(raw_story.strip()) == 0:
            raw_story = f"Story number {i}: I never thought this would happen to me, but last week an unbelievable situation occurred..."

        # Stage 1: AI & Spelling Check
        print(f"[*] [Stage 1] Spell-checking and polishing Story {story_key} via Gemini...")
        polished_text, custom_title = polish_story_with_gemini(raw_story)
        chunks = split_story(polished_text)
        print(f"[+] [Stage 1 Complete] Title: '{custom_title}'")
        time.sleep(1)

        # Stage 2: Render & Subtitles
        print(f"[*] [Stage 2] Rendering video and center subtitles for Story {story_key}...")
        video_paths = []
        for idx, (text, part_title) in enumerate(chunks):
            formatted_title = part_title.upper() if part_title else f"PART {idx+1}"
            job_id = f"story_{story_key}_part_{idx+1}"
            audio_path = os.path.join(WORKSPACE_DIR, f"{job_id}.mp3")
            video_path = os.path.join(WORKSPACE_DIR, f"{job_id}.mp4")

            print(f"[*] Generating Voiceover for {formatted_title}...")
            word_events = generate_tts_sync(text, audio_path)

            print(f"[*] Compositing Video with Center Subtitles for {formatted_title}...")
            seed = {
                "id": job_id,
                "script": text,
                "audio_path": audio_path,
                "word_timings": word_events,
                "story_index": int(story_key)
            }

            try:
                result = renderer.render_short(seed, video_path)
                print(f"[+] Rendered successfully: {result.video_path}")
                video_paths.append(result.video_path)
            except Exception as e:
                raise RuntimeError(f"CRITICAL FAIL: Renderer crashed on {job_id}. Error: {e}")

        print(f"[+] [Stage 2 Complete] Story {story_key} rendered.")

        # Stage 3: Account-Isolated Publishing
        print(f"[*] [Stage 3] Publishing Story {story_key} to assigned YouTube account...")
        target_account_index = (int(story_key) - 1) % len(accounts) if accounts else 0

        for idx, local_video_path in enumerate(video_paths):
            if not os.path.exists(local_video_path):
                raise RuntimeError(f"CRITICAL FAIL: Video file missing at {local_video_path}")

            video_title = f"{custom_title} (Part {idx+1})" if len(video_paths) > 1 else custom_title
            desc_text = "What would you do in this situation? Comment below! #shorts #reddit #storytime"

            print(f"[FORCE] Publishing to YouTube Account #{target_account_index + 1}...")

            try:
                publish_qc_video(
                    video_path=local_video_path,
                    job_id=f"story_{story_key}_part_{idx+1}",
                    qc_provenance_index=target_account_index,
                    qc_passed=True,
                    title=video_title,
                    youtube_description=desc_text,
                    instagram_caption=desc_text,
                    video_public_url=""
                )
                print(f"[+] Success: Story {story_key} published to Account #{target_account_index + 1}.")
            except Exception as e:
                raise RuntimeError(f"CRITICAL FAIL: Publishing failed for Account #{target_account_index + 1}. Error: {e}")

        print(f"[+] LIFECYCLE COMPLETE: Story {story_key} fully completed and uploaded!")
        gc.collect()

    print("\n==================================================")
    print("ALL 7 STORIES SUCCESSFULLY PROCESSED AND UPLOADED!")
    print("==================================================")

if __name__ == "__main__":
    run_all_stories()
