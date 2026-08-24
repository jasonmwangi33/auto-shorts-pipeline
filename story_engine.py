#!/usr/bin/env python3
"""
Story Engine: Narrative reconstruction, strict factuality, local word-count pre-filtering, 
Python-owned weighted score calculation, deterministic failure classification, 
and job-global LLM budget enforcement (max 15 calls).
"""

import json
import logging
import os
from typing import Any, Dict, Iterator, List, Optional

logger = logging.getLogger("story_engine")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

class GlobalLLMBudget:
    """Job-global LLM call tracker ensuring the entire pipeline cannot exceed max calls."""
    def __init__(self, max_calls: int = 15):
        self.max_calls = max_calls
        self.calls_made = 0

    def consume(self) -> bool:
        if self.calls_made >= self.max_calls:
            return False
        self.calls_made += 1
        return True

REWRITER_SYSTEM_PROMPT = """You are an expert short-form narrative writer. Your task is to transform raw source text into a compelling, self-contained micro-story script suitable for 30–60 seconds of fast-paced narration.

STRICT CONSTRAINTS:
1. Factuality (Invariant): You must NEVER invent important events, dialogue, outcomes, names, or motivations not supported by the source material. Improve structure and wording; do not manufacture underlying facts or endings.
2. Word Count: The target script length must be strictly between 90 and 150 words.
3. Structure: Follow a natural narrative arc:
   - Hook: Start immediately inside the story. No introductory remarks, no meta-commentary, no mentioning Reddit or videos.
   - Context & Development: Keep the timeline clear and logical.
   - Payoff: End with the actual conclusion, twist, or resolution present in the source text.
4. Tone: Conversational, engaging, and completely clear to a stranger with zero internet background context.

Return a valid JSON object matching this exact schema:
{
    "script": "The complete rewritten narrative script text..."
}
"""

JUDGE_SYSTEM_PROMPT = """You are an elite Content Quality Director for high-retention short-form video channels. Your role is strictly to evaluate whether a finalized narration script meets rigid quality thresholds. You do not rewrite or fix scripts; you only judge them.

EVALUATION CRITERIA (Score each 0-10):
- standalone_score: Can a stranger understand this with zero Reddit or internet context?
- hook_score: Does the first sentence drop the listener straight into the action with zero intro/meta filler?
- clarity_score: Is the language clear and natural when spoken aloud?
- coherence_score: Is the narrative logical and free of fragmented shifts?
- payoff_score: Is there a legitimate conclusion, twist, or resolution?

Return a valid JSON object matching this exact schema:
{
    "standalone_score": integer (0-10),
    "hook_score": integer (0-10),
    "clarity_score": integer (0-10),
    "coherence_score": integer (0-10),
    "payoff_score": integer (0-10),
    "reason": "Detailed qualitative summary of why it passes or fails."
}
"""

def call_llm(system_prompt: str, user_content: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": system_prompt}, 
            {"role": "user", "content": user_content}
        ],
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content

def reconstruct_narrative(raw_candidate: Dict[str, Any], budget: GlobalLLMBudget) -> Optional[str]:
    if not budget.consume():
        logger.warning("LLM budget exhausted before rewriter call.")
        return None
    headline = raw_candidate.get("headline", "")
    source_text = raw_candidate.get("text", headline)
    user_prompt = f"Source Headline/Content:\n{headline}\n\nAdditional Text:\n{source_text}"
    try:
        raw_res = call_llm(REWRITER_SYSTEM_PROMPT, user_prompt)
        parsed = json.loads(raw_res)
        if isinstance(parsed, dict) and "script" in parsed:
            return parsed["script"].strip()
        logger.warning("Rewriter response did not contain a valid 'script' field.")
        return None
    except Exception as exc:
        logger.error("Narrative reconstruction failed: %s", exc)
        return None

def calculate_weighted_score(standalone: int, hook: int, clarity: int, coherence: int, payoff: int) -> float:
    weighted = (
        (standalone * 3.0) +
        (hook * 2.5) +
        (clarity * 1.25) +
        (coherence * 1.25) +
        (payoff * 2.0)
    )
    return round(weighted, 2)

def evaluate_script(script: str, budget: GlobalLLMBudget) -> Dict[str, Any]:
    actual_word_count = len(script.split())
    if not budget.consume():
        logger.warning("LLM budget exhausted before judge evaluation.")
        return {"passed": False, "score": 0.0, "word_count": actual_word_count, "failure_type": "other", "reason": "Budget exhausted"}
    try:
        raw_eval = call_llm(JUDGE_SYSTEM_PROMPT, f"Script to evaluate:\n\n{script}")
        data = json.loads(raw_eval)
        
        standalone = data.get("standalone_score", 0)
        hook = data.get("hook_score", 0)
        clarity = data.get("clarity_score", 0)
        coherence = data.get("coherence_score", 0)
        payoff = data.get("payoff_score", 0)
        
        final_score = calculate_weighted_score(standalone, hook, clarity, coherence, payoff)
        data["score"] = final_score
        
        failure_type = None
        if actual_word_count < 90:
            failure_type = "too_short"
        elif actual_word_count > 150:
            failure_type = "too_long"
        elif standalone < 8:
            failure_type = "context_dependency"
        elif hook < 8:
            failure_type = "weak_hook"
        elif payoff < 7:
            failure_type = "weak_payoff"
        elif clarity < 7:
            failure_type = "low_clarity"
        elif coherence < 7:
            failure_type = "low_coherence"
        elif final_score < 80:
            failure_type = "other"

        passed = (
            final_score >= 80
            and standalone >= 8
            and hook >= 8
            and payoff >= 7
            and clarity >= 7
            and coherence >= 7
            and 90 <= actual_word_count <= 150
            and failure_type is None
        )
        
        data["passed"] = passed
        data["word_count"] = actual_word_count
        data["failure_type"] = failure_type if not passed else None
        
        if passed and not data.get("reason"):
            data["reason"] = "Script successfully passed all deterministic quality and constraint evaluations."
            
        return data
    except Exception as exc:
        logger.error("Quality gate evaluation failed: %s", exc)
        return {
            "passed": False,
            "score": 0.0,
            "word_count": actual_word_count,
            "failure_type": "other",
            "reason": str(exc)
        }

def process_candidate_stream(
    candidate_supplier: Iterator[Dict[str, Any]], 
    target_count: int = 6, 
    budget: Optional[GlobalLLMBudget] = None
) -> List[Dict[str, Any]]:
    if budget is None:
        budget = GlobalLLMBudget(max_calls=15)
        
    verified_pool: List[Dict[str, Any]] = []
    logger.info("Starting dynamic story intake funnel (Target: %d, Global LLM Budget Limit: %d)", target_count, budget.max_calls)
    
    for candidate in candidate_supplier:
        if len(verified_pool) >= target_count:
            logger.info("Reached verified target count (%d). Stopping intake.", target_count)
            break
            
        script = reconstruct_narrative(candidate, budget)
        if not script:
            continue
            
        words = script.split()
        if len(words) < 90 or len(words) > 150:
            continue
            
        evaluation = evaluate_script(script, budget)
        
        if evaluation.get("passed"):
            verified_pool.append({
                "seed_id": candidate.get("seed_id", f"verified-{len(verified_pool)+1:02d}"),
                "script": script,
                "metrics": evaluation,
                "source": candidate.get("source", "unknown")
            })
            
    logger.info("Funnel complete. Verified pool contains %d/%d target stories. Total LLM calls made: %d.", 
                len(verified_pool), target_count, budget.calls_made)
    return verified_pool
