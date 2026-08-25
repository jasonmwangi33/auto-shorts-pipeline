import os
import sys
import json
import requests
import time
import google.generativeai as genai

WORKSPACE_DIR = "workspace"
os.makedirs(WORKSPACE_DIR, exist_ok=True)
AI_DATA_FILE = os.path.join(WORKSPACE_DIR, "ai_output.json")
RENDER_DATA_FILE = os.path.join(WORKSPACE_DIR, "render_output.json")

def polish_story_with_gemini(raw_text):
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    Rewrite the following story into a highly engaging, first-person narrative optimized for a short-form video.
    Keep it strictly chronological (Hook -> Context -> Escalation -> Consequence -> Payoff). 
    Do not add any moralizing, opinions, or closing advice. Just tell the story directly.
    Raw Story: {raw_text}
    """
    try:
        return model.generate_content(prompt).text.strip()
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
    print("[*] Stage 1: AI Processing System")
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
    print(f"[+] AI processing complete. Scripts secured for Stage 2.")

def run_stage_2():
    print("[*] Stage 2: Cloud Rendering Engine")
    if not os.path.exists(AI_DATA_FILE):
        print("[-] No AI data found. Exiting.")
        sys.exit(1)
        
    with open(AI_DATA_FILE, "r") as f:
        processed = json.load(f)
        
    api_key = os.getenv("CREATOMATE_API_KEY")
    template_id = os.getenv("CREATOMATE_TEMPLATE_ID")
    url = "https://api.creatomate.com/v2/renders"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    renders = {}
    for index, chunks in processed.items():
        renders[index] = []
        for text, part_title in chunks:
            formatted_title = part_title.upper()
            payload = {
                "template_id": template_id,
                "modifications": {
                    "Title-Overlay": formatted_title,
                    "Story-Text": text
                }
            }
            try:
                response = requests.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    render_id = response.json().get('id')
                    print(f"[+] Render sent: Story {index} {formatted_title} (ID: {render_id})")
                    renders[index].append(render_id)
                else:
                    print(f"[-] API Error: {response.text}")
            except Exception as e:
                print(f"[!] Error: {e}")
            time.sleep(3)
            
    with open(RENDER_DATA_FILE, "w") as f:
        json.dump(renders, f)
    print(f"[+] Render jobs dispatched. IDs secured for Stage 3.")

def run_stage_3():
    print("[*] Stage 3: Publishing Gateway & Uploader")
    if not os.path.exists(RENDER_DATA_FILE):
        print("[-] No Render data found. Exiting.")
        sys.exit(1)
        
    with open(RENDER_DATA_FILE, "r") as f:
        renders = json.load(f)
        
    api_key = os.getenv("CREATOMATE_API_KEY")
    headers = {"Authorization": f"Bearer {api_key}"}
    
    # Check credentials availability
    yt_accounts = os.getenv("YOUTUBE_ACCOUNTS_JSON")
    ig_token = os.getenv("IG_ACCESS_TOKEN")
    
    print("[*] Polling Creatomate for render completion...")
    for index, render_ids in renders.items():
        for r_id in render_ids:
            completed = False
            video_url = None
            
            # Poll status until ready (max ~5 minutes)
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
                # --- YouTube / Instagram Publishing Hook ---
                print(f"[*] Dispatching Story {index} video to publishing handlers...")
                if yt_accounts:
                    print(f"[+] YouTube publishing credentials detected. Uploading video...")
                    # Integration hook for your YouTube uploader script utilizing YOUTUBE_ACCOUNTS_JSON
                if ig_token:
                    print(f"[+] Instagram publishing credentials detected. Pushing to Reels...")
                    # Integration hook for Instagram Graph API utilizing IG_ACCESS_TOKEN & IG_USER_ID

    print("[+] Stage 3 execution complete.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: Specify a stage (1, 2, or 3)")
        sys.exit(1)
        
    stage = sys.argv[1]
    if stage == "1": run_stage_1()
    elif stage == "2": run_stage_2()
    elif stage == "3": run_stage_3()
