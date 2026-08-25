import os
import requests
import time

def split_story(text, max_words=150):
    """Splits the story in half if it exceeds the word limit."""
    words = text.split()
    if len(words) <= max_words:
        return [(text, "")] # No split needed
    
    mid = len(words) // 2
    part1 = " ".join(words[:mid])
    part2 = " ".join(words[mid:])
    return [(part1, "Part 1"), (part2, "Part 2")]

def send_to_creatomate(story_text, part_title, index):
    """Fires the API request to Creatomate."""
    api_key = os.getenv("CREATOMATE_API_KEY")
    template_id = os.getenv("CREATOMATE_TEMPLATE_ID")
    
    if not api_key or not template_id:
        print(f"[!] Missing Creatomate API credentials. Skipping Story {index}.")
        return
    
    url = "https://api.creatomate.com/v2/renders"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # We pass the dynamic text to the template via modifications.
    payload = {
        "template_id": template_id,
        "modifications": {
            "Title-Overlay": part_title,
            "Story-Text": story_text 
        }
    }
    
    print(f"[*] Sending Story {index} {part_title} to Creatomate...")
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            print(f"[+] Success! Render job started. ID: {response.json().get('id')}")
        else:
            print(f"[-] API Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"[!] Connection Error: {e}")

def main():
    print("[*] Starting Batch Router Engine...")
    
    # Loop through the 7 text inputs
    for i in range(1, 8):
        story = os.getenv(f"STORY_{i}")
        
        # If the box wasn't left empty, process it
        if story and len(story.strip()) > 0:
            print(f"\n--- Processing Story {i} ---")
            chunks = split_story(story)
            
            for text, part_title in chunks:
                send_to_creatomate(text, part_title, i)
                time.sleep(2) # Stagger API requests to prevent rate limiting

if __name__ == "__main__":
    main()
