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
    Transforms raw source text into a chronological first-person story narration.
    Strictly bans commentary, opinion framing, generic intros, and fact fabrication.
    """
    if not raw_source_text or not isinstance(raw_source_text, str):
        raise TypeError(f"Story engine expects non-empty str, got {type(raw_source_text)}")

    configure_genai()
    model_name = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
    model = genai.GenerativeModel(model_name)
    
    prompt = f"""
You are transforming a personal source account into a spoken, first-person short-form story narration.

CRITICAL DIRECTIVE - CHRONOLOGICAL INCIDENT NARRATION ONLY:
You must reconstruct what happened as an engaging spoken narrative describing a specific event or situation.

STRICT STRUCTURAL PATTERN:
1. HOOK: Open immediately with the core conflict, incident, or problem. 
   Example: "The kid who hit my car was now demanding thirty thousand dollars from me."
2. CONTEXT: Briefly explain who was involved and what the baseline setup was.
3. DEVELOPMENT / ESCALATION: Show what happened step-by-step and how the tension or problem escalated.
4. CONSEQUENCE: Detail what resulted from the escalation.
5. PAYOFF / UNRESOLVED ENDING: Conclude on the final outcome or the unresolved situation.

NEGATIVE CONSTRAINTS (ABSOLUTE BANS):
- NEVER use generic intros or commentary: "Tell me if I'm the only one", "Here is why", "Does anyone else", "So this happened", "In my opinion", "I think people should".
- NEVER explain or analyze the topic. Narrate the incident directly.
- NEVER fabricate facts, characters, dollar amounts, legal consequences, or resolutions not supported by the source text.
- If the source has an uncertain or unresolved outcome, PRESERVE THAT UNCERTAINTY. Do not invent a fake happy ending.
- FORMAT: Spoken prose only. No markdown formatting, bullet points, meta-commentary, or sound effect brackets.

SOURCE TEXT:
{raw_source_text}
"""

    try:
        response = model.generate_content(prompt)
        script_text = response.text.strip()
        if not script_text:
            raise ValueError("Gemini returned empty script text.")
        logger.info("Successfully generated chronological story narrative.")
        return script_text
    except Exception as e:
        logger.error(f"Failed to generate story script via Gemini: {e}")
        return raw_source_text.strip()
