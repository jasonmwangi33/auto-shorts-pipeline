import os
import requests
import time
import google.generativeai as genai

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

def polish_story_with_gemini(raw_text):
    """Uses Gemini to rewrite raw Reddit text into a tight, chronological script."""
    print("[*] Processing raw text through Gemini...")
    prompt = f"""
    Rewrite the following story into a highly engaging, first-person narrative optimized for a short-form video.
    Keep it strictly chronological (Hook -> Context -> Escalation -> Consequence -> Payoff). 
    Do not add any moralizing, opinions, or closing advice. Just tell the story directly.
    
    Raw Story:
    {raw_text}
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"[!] Gemini AI Error: {e}")
        return raw_text 

def split_story(text, max_words=150):
    """Splits the story in half if it exceeds the word limit."""
    words = text.split()
    if len(words) <= max_words:
        return [(text, "")]
    
    mid = len(words) // 2
    part1 = " ".join(words[:mid])
    part2 = " ".join(words[mid:])
    return [(part1, "Part 1"), (part2, "Part 2")]

def send_to_creatomate(story_text, part_title, index):
    """Fires the API request to Creatomate."""
    api_key = os.getenv("CREATOMATE_API_KEY")
    template_id = os.getenv("CREATOMATE_TEMPLATE_ID")
    
    if not api_key or not template_id:
        print(f"[!] Missing Creatomate API credentials. Skipping render.")
        return
    
    url = "https://api.creatomate.com/v2/renders"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # ⚡ AUTOMATIC ALL-CAPS FIX APPLIED HERE ⚡
    formatted_title = part_title.upper()
    
    payload = {
        "template_id": template_id,
        "modifications": {
            "Title-Overlay": formatted_title,
            "Story-Text": story_text 
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            print(f"[+] Render job started for Story {index} {formatted_title}. ID: {response.json().get('id')}")
        else:
            print(f"[-] Creatomate API Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"[!] Connection Error: {e}")

def main():
    print("[*] Starting AI Batch Router Engine...")
    for i in range(1, 8):
        story_input = os.getenv(f"STORY_{i}")
        if story_input and len(story_input.strip()) > 0:
            print(f"\n--- Processing Box {i} ---")
            
            # 1. Rewrite with Gemini
            polished_script = polish_story_with_gemini(story_input)
            
            # 2. Check length and split if needed
            chunks = split_story(polished_script)
            
            # 3. Render via API
            for text, part_title in chunks:
                send_to_creatomate(text, part_title, i)
                time.sleep(3)

if __name__ == "__main__":
    main()
