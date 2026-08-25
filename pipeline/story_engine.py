import os
import logging
import google.generativeai as genai

logger = logging.getLogger("story_engine")

def configure_genai():
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)

def generate_narrative_script(raw_source_text: str) -> str:
    """
    Transforms source text into an elite, high-retention personal drama story, 
    strictly banning boring opinion questions and forcing explosive narrative hooks.
    """
    configure_genai()
    model_name = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
    model = genai.GenerativeModel(model_name)
    
    prompt = f"""
You are an elite, savage viral storyteller who creates the highest-retention Reddit personal drama stories for TikTok and YouTube Shorts.
The source material provided might be dry or poorly formatted. Your job is to completely rewrite and supercharge it into a **fast-paced, high-stakes personal confrontation, betrayal, or revenge story**.

ABSOLUTE BAN (VIOLATIONS WILL RUIN THE VIDEO):
- NEVER start with: "Tell me if I'm the only one", "Does anyone else", "So this happened", "Here's a hot take", or any opinion/shower-thought question. 
- NEVER use passive summaries or boring background exposition.

MANDATORY HOOK (First sentence must grip the viewer instantly by the throat):
- Start mid-conflict, mid-betrayal, or with an explosive realization. 
- Examples of correct hooks: 
  * "My brother thought he could get away with ruining my car, until I walked into his wedding with the police report."
  * "I found out my wife was hiding a thirty-thousand-dollar debt when the repo man showed up at my job."
  * "My parents laughed in my face when I told them I was quitting, until they saw my bank account balance."

STRICT NARRATIVE ARC:
1. THE EXPLOSIVE HOOK (Sentence 1-2): Maximum shock value or dramatic tension. No intro fluff.
2. THE TENSE ESCALATION: Fast, visceral narrative of how things went wrong, featuring concrete stakes (vehicles, cash, legal trouble, family betrayal, specific dollar amounts).
3. THE CLIMAX / PAYOFF: A brutal confrontation, a satisfying reality check, or a jaw-dropping cliffhanger.
4. TONE: Written strictly in the first-person ("I"). Conversational, raw, bitter, or triumphant—like a real person exposing a crazy life event to the internet. 
5. FORMAT: Clean narration text only. No markdown, no timestamps, no brackets, no meta-commentary.

SOURCE TEXT TO TRANSFORM:
{raw_source_text}
"""

    try:
        response = model.generate_content(prompt)
        script_text = response.text.strip()
        logger.info("Successfully generated high-drama personal narrative script.")
        return script_text
    except Exception as e:
        logger.error(f"Failed to generate narrative script via Gemini: {e}")
        return raw_source_text
