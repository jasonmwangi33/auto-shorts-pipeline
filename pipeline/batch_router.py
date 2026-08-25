import os
import requests
import time
import google.generativeai as genai

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

def polish_story_with_gemini(raw_text):
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
        print(f"[!] Gemini AI Error: {e}")
        return raw_text 

def split_story(text, max_words=150):
    words = text.split()
    if len(words) <= max_words:
        return [(text, "")]
    mid = len(words) // 2
    return [(" ".join(words[:mid]), "Part 1"), (" ".join(words[mid:]), "Part 2")]

def send_to_creatomate(story_text, part_title, index):
    api_key = os.getenv("CREATOMATE_API_KEY")
    template_id = os.getenv("CREATOMATE_TEMPLATE_ID")
    
    if not api_key or not template_id:
        print(f"[!] Missing API credentials.")
        return None
        
    url = "https://api.creatomate.com/v2/renders"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "template_id": template_id,
        "modifications": {
            "Title-Overlay": part_title.upper(),
            "Story-Text": story_text 
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            render_id = response.json().get('id')
            print(f"[+] Render started for Story {index} {part_title.upper()}. ID: {render_id}")
            return render_id
        else:
            print(f"[-] Render Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"[!] Connection Error: {e}")
    return None

def main():
    print("\n==================================================")
    print("  STAGE 1: AI SYSTEM PROCESSING")
    print("==================================================")
    processed_scripts = {}
    
    for i in range(1, 8):
        story_input = os.getenv(f"STORY_{i}")
        if story_input and len(story_input.strip()) > 0:
            print(f"[*] Processing Story {i} via AI...")
            polished_script = polish_story_with_gemini(story_input)
            chunks = split_story(polished_script)
            processed_scripts[i] = chunks
            time.sleep(2) # Prevent API rate limits

    if not processed_scripts:
        print("[-] No stories provided. Exiting pipeline.")
        return

    print("\n==================================================")
    print("  STAGE 2: CLOUD RENDERING & FILTERS")
    print("==================================================")
    active_renders = []
    
    for index, chunks in processed_scripts.items():
        for text, part_title in chunks:
            render_id = send_to_creatomate(text, part_title, index)
            if render_id:
                active_renders.append(render_id)
            time.sleep(3) # Stagger API payload requests

    print("\n==================================================")
    print("  STAGE 3: PUBLISHING")
    print("==================================================")
    print(f"[*] Awaiting completion of {len(active_renders)} render tasks...")
    print("[*] System initialized for auto-publishing APIs. (Awaiting Platform Integration)")
    # Future logic: Loop through active_renders, wait for status="succeeded", then push to social APIs.

if __name__ == "__main__":
    main()
