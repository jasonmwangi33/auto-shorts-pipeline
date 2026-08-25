import os
import sys
import json
import time
import requests

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
    Rewrite the following story into a highly engaging, first-person narrative optimized for a short-form video.
    Keep it strictly chronological (Hook -> Context -> Escalation -> Consequence -> Payoff). 
    Do not add any moralizing, opinions, or closing advice. Just tell the story directly.
    Raw Story: {raw_text}
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"[!] Gemini Error: {e}")
        return raw_text

def split_story(text, max_words=150):
    words = text.split()
    if len(words) <= max_words:
        return [(text, "")]
    mid = len(words) // 2
    return [(" ".join(words[:mid]), "Part 1"), (" ".join(words[mid:]), "Part 2")]

def run_stage_1():
    print("[*] Stage 1: AI Scavenger & Processing System")
    processed = {}
    for i in range(1, 8):
        story = os.getenv(f"STORY_{i}")
        if story and len(story.strip()) > 0:
            print(f"[*] AI Rewriting Story {i}...")
            polished = polish_story_with_gemini(story)
            processed[str(i)] = split_story(polished)
            time.sleep(2)
    
    if not processed:
        print("[-] No stories provided. Stopping pipeline.")
        sys.exit(0)

    with open(AI_DATA_FILE, "w") as f:
        json.dump(processed, f)
    print(f"[+] AI processing complete. Scripts secured for Matrix Workers.")

def run_stage_2(story_id):
    print(f"[*] Stage 2: Cloud Rendering Worker for Story ID: {story_id}")
    if not os.path.exists(AI_DATA_FILE):
        print("[-] No AI data found. Exiting.")
        sys.exit(1)
        
    with open(AI_DATA_FILE, "r") as f:
        processed = json.load(f)
        
    story_key = str(story_id)
    if story_key not in processed:
        print(f"[*] No story content found for slot {story_id}. Skipping worker.")
        return

    api_key = os.getenv("CREATOMATE_API_KEY")
    template_id = os.getenv("CREATOMATE_TEMPLATE_ID")
    url = "https://api.creatomate.com/v2/renders"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    chunks = processed[story_key]
    renders = {}
    if os.path.exists(RENDER_DATA_FILE):
        try:
            with open(RENDER_DATA_FILE, "r") as f:
                renders = json.load(f)
        except:
            pass

    renders[story_key] = []
    for idx, (text, part_title) in enumerate(chunks):
        formatted_title = part_title.upper() if part_title else f"PART {idx+1}"
        payload = {
            "template_id": template_id,
            "modifications": {
                "Title-Overlay": formatted_title,
                "Story-Text": text
            }
        }
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code in [200, 201]:
                render_id = response.json().get('id')
                print(f"[+] Render sent: Story {story_key} {formatted_title} (ID: {render_id})")
                renders[story_key].append(render_id)
            else:
                print(f"[-] API Error: {response.text}")
        except Exception as e:
            print(f"[!] Error: {e}")
        time.sleep(2)
        
    with open(RENDER_DATA_FILE, "w") as f:
        json.dump(renders, f)
    print(f"[+] Render state saved for Story {story_key}.")

def run_stage_3():
    print("[*] Stage 3: Unified Publisher & Uploader")
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    try:
        from publishers.manager import publish_qc_video
    except ImportError:
        publish_qc_video = None

    # Gather all render state files from workspace_all (matrix artifacts download structure)
    all_renders = {}
    workspace_all = "workspace_all"
    if os.path.exists(workspace_all):
        for root, dirs, files in os.walk(workspace_all):
            if "render_output.json" in files:
                try:
                    with open(os.path.join(root, "render_output.json"), "r") as f:
                        data = json.load(f)
                        all_renders.update(data)
                except Exception as e:
                    print(f"[-] Error reading render state artifact: {e}")

    # Fallback to local workspace if running single node
    if not all_renders and os.path.exists(RENDER_DATA_FILE):
        with open(RENDER_DATA_FILE, "r") as f:
            all_renders = json.load(f)

    if not all_renders:
        print("[-] No render outputs found across matrix slots. Exiting.")
        sys.exit(1)

    api_key = os.getenv("CREATOMATE_API_KEY")
    headers = {"Authorization": f"Bearer {api_key}"}
    
    print("[*] Polling Creatomate for render completion across all slots...")
    for index, render_ids in all_renders.items():
        for idx, r_id in enumerate(render_ids):
            completed = False
            video_url = None
            
            for _ in range(30):
                res = requests.get(f"https://api.creatomate.com/v2/renders/{r_id}", headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    status = data.get("status")
                    if status == "succeeded":
                        video_url = data.get("url")
                        print(f"[+] Render {r_id} succeeded! URL: {video_url}")
                        completed = True
                        break
                    elif status == "failed":
                        print(f"[-] Render {r_id} failed.")
                        break
                time.sleep(10)
            
            if completed and video_url:
                local_video_path = os.path.join(WORKSPACE_DIR, f"story_{index}_part_{idx+1}.mp4")
                print(f"[*] Downloading video from Creatomate to {local_video_path}...")
                vid_res = requests.get(video_url)
                with open(local_video_path, "wb") as f:
                    f.write(vid_res.content)
                
                print(f"[*] Dispatching Story {index} Part {idx+1} to Publisher Manager...")
                if publish_qc_video:
                    try:
                        title_text = f"Reddit Story - Part {idx+1}"
                        desc_text = "Check out this wild Reddit story! #shorts #reddit"
                        report = publish_qc_video(
                            video_path=local_video_path,
                            job_id=f"story_{index}_part_{idx+1}",
                            qc_passed=True,
                            title=title_text,
                            youtube_description=desc_text,
                            instagram_caption=desc_text,
                            video_public_url=video_url
                        )
                        print(f"[+] Publishing Report: {report}")
                    except Exception as e:
                        print(f"[!] Publishing execution error: {e}")
                        raise
                else:
                    print("[-] publish_qc_video function could not be loaded.")

    print("[+] Stage 3 execution complete.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: Specify a stage (1, 2, or 3)")
        sys.exit(1)
        
    stage = sys.argv[1]
    if stage == "1":
        run_stage_1()
    elif stage == "2":
        story_id = sys.argv[2] if len(sys.argv) > 2 else 1
        run_stage_2(story_id)
    elif stage == "3":
        run_stage_3()

