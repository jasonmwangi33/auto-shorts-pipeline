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
    Transforms raw source text into a high-retention, hyper-engaging personal drama narrative
    modeled after top viral TikTok/YouTube Reddit story creators.
    """
    configure_genai()
    model_name = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
    model = genai.GenerativeModel(model_name)
    
    prompt = f"""
You are an elite viral storyteller specializing in high-drama personal conflict narratives for TikTok and YouTube Shorts.
Analyze the following source text.

CORE REQUIREMENTS FOR THE SCRIPT:
1. THE HOOK (First 2 seconds): Start immediately with a shocking event, consequence, or confrontation (e.g., "My car was totaled, and now the kid who hit me is suing ME for his emotional damage...", "I never expected my own father to laugh in my face when I showed him the police report..."). Never use generic intros.
2. CONCRETE STAKES: Emphasize real-world elements like vehicles, money, specific dollar amounts, legal threats, or family betrayal. Avoid vague philosophical statements.
3. RISING ACTION & PACING: Keep the tension high. Show the conflict unfolding step-by-step with natural, conversational spoken dialogue pacing.
4. CLIFFHANGER / PAYOFF: End on a satisfying turning point, a brutal realization, or an unresolved dilemma that hooks the viewer to the very last second.
5. FORMAT: Clean, raw narration text only. No markdown, no timestamps, no brackets, no meta-commentary.

SOURCE TEXT TO ADAPT:
{raw_source_text}
"""

    try:
        response = model.generate_content(prompt)
        script_text = response.text.strip()
        logger.info("Successfully generated high-stakes personal drama script.")
        return script_text
    except Exception as e:
        logger.error(f"Failed to generate narrative script via Gemini: {e}")
        return raw_source_text
