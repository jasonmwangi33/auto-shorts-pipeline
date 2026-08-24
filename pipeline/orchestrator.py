#!/usr/bin/env python3
"""
Orchestrator Module: Integrates the Story Quality Gate with a job-global LLM budget,
dynamic seed generation, and independent visual theme assignment per render job.
"""

import json
import logging
from pathlib import Path
from story_engine import process_candidate_stream, GlobalLLMBudget
from pipeline.visuals import select_visual_theme

logger = logging.getLogger("orchestrator")

def prepare_render_manifest(raw_candidates_supplier, target_count: int = 6, max_llm_calls: int = 15) -> list:
    global_budget = GlobalLLMBudget(max_calls=max_llm_calls)
    verified_stories = process_candidate_stream(raw_candidates_supplier, target_count=target_count, budget=global_budget)
    
    manifest = []
    for story in verified_stories:
        visual_theme = select_visual_theme()
        manifest.append({
            "seed_id": story.get("seed_id"),
            "story": story,
            "visual_theme": visual_theme
        })
        
    seed_path = Path("seeds.json")
    seed_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info("Successfully wrote %d verified seeds to seeds.json", len(manifest))
    return manifest
