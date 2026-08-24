#!/usr/bin/env python3
import json
import logging
import os
from typing import Any, Dict, Iterator, List, Optional

logger = logging.getLogger("story_engine")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

class GlobalLLMBudget:
    def __init__(self, max_calls: int = 15):
        self.max_calls = max_calls
        self.calls_made = 0
    def consume(self) -> bool:
        if self.calls_made >= self.max_calls: return False
        self.calls_made += 1
        return True

PIPELINE_LLM_BUDGET = GlobalLLMBudget(15)

REWRITER_SYSTEM_PROMPT = """You are an expert short-form narrative writer. 
STRICT CONSTRAINTS:
1. Factuality: NEVER invent events, dialogue, outcomes, names, or motivations not in the source.
2. Word Count: 90 to 150 words inclusive.
3. Hook: Start immediately inside the story. No meta-commentary.
4. Payoff: End with the actual conclusion or resolution.
Return JSON ONLY: {"script": "The complete rewritten narrative script text..."}"""

JUDGE_SYSTEM_PROMPT = """You are a Content Quality Director. Evaluate the finalized script.
Score 0-10 for: standalone_score, hook_score, clarity_score, coherence_score, payoff_score.
Return JSON ONLY: {"standalone_score": 0, "hook_score": 0, "clarity_score": 0, "coherence_score": 0, "payoff_score": 0, "reason": "..."}"""

def call_llm(system_prompt: str, user_content: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}],
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content

def reconstruct_narrative(raw_candidate: Dict[str, Any]) -> Optional[str]:
    headline = raw_candidate.get("headline", "")
    source_text = raw_candidate.get("text", headline)
    try:
        raw_res = call_llm(REWRITER_SYSTEM_PROMPT, f"Headline:\n{headline}\n\nText:\n{source_text}")
        parsed = json.loads(raw_res)
        return parsed["script"].strip() if isinstance(parsed, dict) and "script" in parsed else None
    except Exception as exc:
        logger.error("Narrative reconstruction failed: %s", exc)
        return None

def evaluate_script(script: str) -> Dict[str, Any]:
    actual_word_count = len(script.split())
    try:
        raw_eval = call_llm(JUDGE_SYSTEM_PROMPT, f"Script to evaluate:\n\n{script}")
        data = json.loads(raw_eval)
        
        standalone = data.get("standalone_score", 0)
        hook = data.get("hook_score", 0)
        clarity = data.get("clarity_score", 0)
        coherence = data.get("coherence_score", 0)
        payoff = data.get("payoff_score", 0)
        
        final_score = round((standalone * 3.0) + (hook * 2.5) + (clarity * 1.25) + (coherence * 1.25) + (payoff * 2.0), 2)
        data["score"] = final_score
        
        failure_type = None
        if actual_word_count < 90: failure_type = "too_short"
        elif actual_word_count > 150: failure_type = "too_long"
        elif standalone < 8: failure_type = "context_dependency"
        elif hook < 8: failure_type = "weak_hook"
        elif payoff < 7: failure_type = "weak_payoff"
        elif clarity < 7: failure_type = "low_clarity"
        elif coherence < 7: failure_type = "low_coherence"
        elif payoff < 8 and final_score < 85: failure_type = "incomplete_arc"
        elif coherence < 8: failure_type = "fragmented_logic"
        elif final_score < 80: failure_type = "other"

        passed = (final_score >= 80 and standalone >= 8 and hook >= 8 and payoff >= 7 and clarity >= 7 and coherence >= 7 and 90 <= actual_word_count <= 150 and failure_type is None)
        
        data.update({"passed": passed, "word_count": actual_word_count, "failure_type": failure_type})
        return data
    except Exception as exc:
        return {"passed": False, "score": 0.0, "word_count": actual_word_count, "failure_type": "other", "reason": str(exc)}

def process_candidate_stream(candidate_supplier: Iterator[Dict[str, Any]], target_count: int = 6, budget: GlobalLLMBudget = PIPELINE_LLM_BUDGET) -> List[Dict[str, Any]]:
    verified_pool = []
    for candidate in candidate_supplier:
        if len(verified_pool) >= target_count or not budget.consume(): break
        script = reconstruct_narrative(candidate)
        if not script or len(script.split()) < 90 or len(script.split()) > 150: continue
        if not budget.consume(): break
        evaluation = evaluate_script(script)
        if evaluation.get("passed"):
            verified_pool.append({
                "seed_id": candidate.get("seed_id", f"verified-{len(verified_pool)+1:02d}"),
                "script": script, "metrics": evaluation, "source": candidate.get("source", "unknown")
            })
    return verified_pool
