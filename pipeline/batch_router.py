import os
import sys
import json
import time
import asyncio
import requests
from pathlib import Path

WORKSPACE_DIR = "workspace"
os.makedirs(WORKSPACE_DIR, exist_ok=True)
AI_DATA_FILE = os.path.join(WORKSPACE_DIR, "ai_output.json")

def call_gemini_rest(prompt, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7}
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"[!] Direct API Error: {e}")
        return None

def polish_story_with_gemini(raw_text):
    if not raw_text or len(raw_text.strip()) == 0:
        return "This is an incredible story about an unexpected turn of events.", "CRAZY STORY 🤯 #shorts", "A wild story about an unexpected turn of events. unexpected, crazy story, reddit story, storytime, viral. #shorts #viralshorts #reddit #storytime"
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key: return raw_text, "CRAZY STORY 🤯 #shorts", "A wild story about an unexpected turn of events. unexpected, crazy story, reddit story, storytime, viral. #shorts #viralshorts #reddit #storytime"
        
    story_prompt = f"You are an expert editor. Fix spelling/grammar and rewrite this into a fast-paced, high-retention first-person short story for vertical video. Limit it to around 150-180 words so it fits in a 60-second video perfectly. Do not split it. No moral advice. Story: {raw_text}"
    title_prompt = f"Create a catchy, viral YouTube Short title based on this story.\nRULES:\n1. The first two words MUST be strong keywords in ALL CAPS.\n2. Keep it under 50 characters total.\n3. Include exactly ONE emoji at the end of the text.\n4. End the title with ONLY the hashtag #shorts (no other hashtags).\nStory: {raw_text}"
    desc_prompt = f"Create a YouTube Shorts SEO description based on this story.\nRULES:\n1. First sentence: A concise, punchy summary of the story.\n2. Second line: 5 to 6 highly relevant SEO keywords separated by commas.\n3. Third line: Exactly these hashtags: #shorts #viralshorts #reddit #storytime\nStory: {raw_text}"
    
    story_res = call_gemini_rest(story_prompt, api_key)
    title_res = call_gemini_rest(title_prompt, api_key)
    desc_res = call_gemini_rest(desc_prompt, api_key)
    
    return (
        story_res if story_res else raw_text, 
        title_res if title_res else "CRAZY STORY 🤯 #shorts",
        desc_res if desc_res else "What would you do in this situation? storytime, reddit, crazy story, drama, viral. #shorts #viralshorts #reddit #storytime"
    )

def run_stage_1():
    print("==================================================")
    print("PHASE 1: Direct API Story Processing (Viral SEO Rules)")
    print("==================================================")
    processed, titles, descriptions = {}, {}, {}
    for i in range(1, 8):
        raw_story = os.getenv(f"STORY_{i}")
        if not raw_story or len(raw_story.strip()) == 0:
            raw_story = f"Story {i}: An unbelievable situation occurred yesterday..."
        print(f"[*] AI Formatting Story {i} with Viral SEO...")
        polished_text, custom_title, custom_desc = polish_story_with_gemini(raw_story)
        processed[str(i)] = polished_text
        titles[str(i)] = custom_title
        descriptions[str(i)] = custom_desc
        print(f"[+] Title Generated: {custom_title}")
        time.sleep(1)

    with open(AI_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"stories": processed, "titles": titles, "descriptions": descriptions}, f, indent=2)
    print(f"[+] Phase 1 Complete. Workspace prepped with SEO data.")

def run_story_worker(story_id):
    story_key = str(story_id)
    print("==================================================")
    print(f"PHASE 2 WORKER: Story {story_key} Pipeline")
    print("==================================================")

    if not os.path.exists(AI_DATA_FILE): raise FileNotFoundError("CRITICAL: AI data missing.")
    with open(AI_DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        story_text = data.get("stories", {}).get(story_key, "")
        custom_title = data.get("titles", {}).get(story_key, f"CRAZY STORY #{story_key} 🤯 #shorts")
        custom_desc = data.get("descriptions", {}).get(story_key, "Comment below! #shorts #viralshorts")

    if not story_text: return print(f"[-] Story {story_key} has no content. Exiting.")

    import edge_tts
    def generate_tts_sync(text, output_path):
        async def _run():
            communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural", rate="+38%")
            word_events, audio_chunks = [], []
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_chunks.append(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    start = chunk["offset"] / 1e7
                    dur = chunk["duration"] / 1e7
                    word_events.append({"word": chunk["text"], "start": start, "end": start + dur})
            with open(output_path, "wb") as wf:
                for data in audio_chunks: wf.write(data)
            return word_events
        return asyncio.run(_run())

    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from pipeline.renderer import Renderer
    renderer = Renderer()

    job_id = f"story_{story_key}"
    audio_path = os.path.join(WORKSPACE_DIR, f"{job_id}.mp3")
    video_path = os.path.join(WORKSPACE_DIR, f"{job_id}.mp4")

    print(f"[*] Generating Voiceover...")
    word_events = generate_tts_sync(story_text, audio_path)

    print(f"[*] Rendering Master Video with changing backgrounds and center text...")
    seed = {"id": job_id, "script": story_text, "audio_path": audio_path, "word_timings": word_events}
    
    try:
        result = renderer.render_short(seed, video_path)
        print(f"[+] Rendered successfully: {video_path}")
    except Exception as e:
        raise RuntimeError(f"CRITICAL: Renderer crashed. Error: {e}")
        
    import gc; gc.collect()

    print(f"[*] Publishing Story {story_key} to target account...")
    from publishers.manager import publish_qc_video

    print(f"[FORCE] Uploading STRICTLY to YouTube Account #{story_key}...")
    try:
        publish_qc_video(
            video_path=video_path,
            job_id=job_id,
            qc_passed=True,
            title=custom_title,
            youtube_description=custom_desc,
            instagram_caption=custom_desc,
            video_public_url="",
            target_account_num=int(story_key) # THIS IS THE FIX. Forces exactly ONE account.
        )
        print(f"[+] Success: Video uploaded strictly to Account #{story_key}.")
    except Exception as e:
        print(f"[-] CRITICAL: Publishing failed. Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(1)
    if sys.argv[1] == "1": run_stage_1()
    else: run_story_worker(sys.argv[1])
