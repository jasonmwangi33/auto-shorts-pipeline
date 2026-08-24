import os
import logging
import google.generativeai as genai

logger = logging.getLogger("story_engine")

def configure_genai():
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)

def generate_narrative_script(raw_source_text: str) -> str:
    """Transforms raw Reddit text into a gripping, first-person narrative arc with natural hooks and payoffs."""
    configure_genai()
    model_name = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
    model = genai.GenerativeModel(model_name)
    
    prompt = f"""
You are an expert viral storyteller specializing in gripping Reddit narratives for short-form video.
Analyze the following source text and reconstruct it into a coherent, compelling first-person narrative script.

SOURCE TEXT:
{raw_source_text}

STRICT INSTRUCTIONS:
1. IDENTIFY THE CORE CONFLICT: Determine if this is a personal story, AITA conflict, relationship dilemma, or question. Preserve the original framing and ambiguity if the source asks a question.
2. NARRATIVE ARC: Structure the script with:
   - A compelling HOOK (a natural question like "Would you have done the same?", "Was she actually in the wrong here?", or an intriguing setup).
   - SETUP & CONTEXT (Who is involved, what was the situation).
   - DEVELOPMENT & ESCALATION (The tension building up).
   - OUTCOME & PAYOFF / QUESTION (Ending with the natural reflection or question for the audience).
3. TONE & STYLE: Must sound like a real person naturally telling another person what happened. Conversational, high-engagement, perfectly paced. Avoid robotic summaries.
4. FORMAT: Output only the clean narration script text without markdown headers.
"""
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Failed to generate narrative script: {e}")
        return raw_source_text
