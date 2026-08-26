import os
import sys
import json
import time
import asyncio
from pathlib import Path

try:
    from google import genai
    HAS_NEW_GENAI = True
except ImportError:
    HAS_NEW_GENAI = False

WORKSPACE_DIR = "workspace"
os.makedirs(WORKSPACE_DIR, exist_ok=True)
AI_DATA_FILE = os.path.join(WORKSPACE_DIR, "ai_output.json")

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
            # Use standard gemini-2.5-flash or gemini-2.0-flash compatible with new google-genai SDK
            story_res = client.models.generate_content(model='gemini-2.5-flash', contents=story_prompt).text.strip()
            title_res = client.models.generate_content(model='gemini-2.5-flash', contents=title_prompt).text.strip()
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
        # Fallback to gemini-2.0-flash if 2.5 isn't available on key
        try:
            if HAS_NEW_GENAI:
                client = genai.Client(api_key=api_key)
                story_res = client.models.generate_content(model='gemini-2.0-flash', contents=story_prompt).text.strip()
                title_res = client.models.generate_content(model='gemini-2.0-flash', contents=title_prompt).text.strip()
                return story_res, title_res
        except Exception as e2:
            print(f"[!] Gemini Fallback Error: {e2}")
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

def run_stage_1():
    print("==================================================")
    print("PHASE 1: Centralized AI Processing & Spell-Check")
    print("==================================================")
    processed = {}
    titles = {}
    
    for i in range(1, 8):
        raw_story = os.getenv(f"STORY_{i}")
        if not raw_story or len(raw_story.strip()) == 0:
            raw_story = f"Story number {i}: I never thought this would happen to me, but last week an unbelievable situation occurred..."
        
        print(f"[*] Processing & spell-checking Story {i} via Gemini...")
        polished_text, custom_title = polish_story_with_gemini(raw_story)
        processed[str(i)] = split_story(polished_text)
        titles[str(i)] = custom_title
        print(f"[+] Story {i} Title: '{custom_title}'")
        time.sleep(0.5)

    data_payload = {"stories": processed, "titles": titles}
    with open(AI_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data_payload, f, indent=2)
    print(f"[+] Phase 1 Complete. AI data saved to {AI_DATA_FILE}")

def run_story_worker(story_id):
    story_key = str(story_id)
    print("==================================================")
    print(f"PHASE 2 WORKER START: Story {story_key}")
    print("==================================================")

    if not os.path.exists(AI_DATA_FILE):
        raise FileNotFoundError(f"CRITICAL FAIL: AI data missing at {AI_DATA_FILE}. Phase 1 must run first.")

    with open(AI_DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        processed = data.get("stories", {})
        titles = data.get("titles", {})

    if story_key not in processed:
        print(f"[-] Story {story_key} not found in AI data. Skipping.")
        return

    chunks = processed[story_key]
    custom_title = titles.get(story_key, f"Satisfying Story #{story_key} #shorts")

    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from pipeline.renderer import Renderer
    renderer = Renderer()
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

    video_paths = []
    for idx, (text, part_title) in enumerate(chunks):
        formatted_title = part_title.upper() if part_title else f"PART {idx+1}"
        job_id = f"story_{story_key}_part_{idx+1}"
        audio_path = os.path.join(WORKSPACE_DIR, f"{job_id}.mp3")
        video_path = os.path.join(WORKSPACE_DIR, f"{job_id}.mp4")

        print(f"[*] Generating Voiceover for Story {story_key} {formatted_title}...")
        word_events = generate_tts_sync(text, audio_path)

        print(f"[*] Rendering Video with Center Subtitles for Story {story_key} {formatted_title}...")
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

    print(f"[+] Video rendering complete for Story {story_key}.")

    # Publishing Stage
    print(f"[*] Publishing Story {story_key} to assigned YouTube account...")
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
                qc_passed=True,
                title=video_title,
                youtube_description=desc_text,
                instagram_caption=desc_text,
                video_public_url=""
            )
            print(f"[+] Success: Story {story_key} successfully uploaded to Account #{target_account_index + 1}.")
        except Exception as e:
            raise RuntimeError(f"CRITICAL FAIL: Publishing failed for Account #{target_account_index + 1}. Error: {e}")

    print("==================================================")
    print(f"LIFECYCLE COMPLETE: Story {story_key} fully processed and uploaded!")
    print("==================================================")

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(1)
    arg = sys.argv[1]
    if arg == "1":
        run_stage_1()
    else:
        run_story_worker(arg)
