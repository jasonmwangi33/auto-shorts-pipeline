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
    Transforms raw Reddit text into a gripping, first-person narrative story 
    strictly avoiding abstract shower thoughts or generic philosophical musings.
    """
    configure_genai()
    model_name = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
    model = genai.GenerativeModel(model_name)
    
    prompt = f"""
You are an expert viral storyteller specializing in gripping Reddit personal narratives for short-form video.
Analyze the following source text. 

CRITICAL RULE: 
- Reject abstract philosophical musings, shower thoughts, or vague observations (e.g., "does anyone else notice X about the human brain"). 
- ONLY process posts that describe a real interpersonal conflict, family drama, relationship dilemma, workplace tension, or shocking personal event that happened to someone.

SOURCE TEXT:
{raw_source_text}

STRICT NARRATIVE STRUCTURE TO BUILD:
1. THE HOOK: Start directly with the action or a gripping dilemma (e.g., "When I was 8 years old...", "My husband thought he could hide this from me..."). Never use generic AI intros like "Here's a hot take."
2. THE SETUP & CONTEXT: Explain who was involved and what the baseline situation was.
3. THE ESCALATION: Detail the conflict or turning point where things went wrong.
4. THE PAYOFF / QUESTION: End on the shocking outcome or a natural question ("Was I wrong for doing what I did?", "Would you have done the same?").
5. TONE: Natural, conversational, like someone telling a friend what happened. No markdown, no meta-commentary, clean narration text only.
"""

    try:
        response = model.generate_content(prompt)
        script_text = response.text.strip()
        logger.info("Successfully generated strict personal narrative script.")
        return script_text
    except Exception as e:
        logger.error(f"Failed to generate narrative script via Gemini: {e}")
        return raw_source_text
