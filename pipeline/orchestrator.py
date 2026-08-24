#!/usr/bin/env python3
import json
import logging
from pathlib import Path
from story_engine import process_candidate_stream, PIPELINE_LLM_BUDGET
from pipeline.visuals import select_visual_theme

logger = logging.getLogger("orchestrator")

class JobOrchestrator:
    def __init__(self, config: dict):
        self.config = config

    def run_job(self, seed_data: dict):
        """Runs the individual render and upload job for a given seed."""
        logger.info("Executing job for seed: %s", seed_data.get("seed_id"))
        # Preserving core execution pipeline integration point

def prepare_render_manifest(raw_candidates_supplier, target_count: int = 6) -> list:
    verified_stories = process_candidate_stream(raw_candidates_supplier, target_count=target_count, budget=PIPELINE_LLM_BUDGET)
    manifest = [{"seed_id": s.get("seed_id"), "story": s, "visual_theme": select_visual_theme()} for s in verified_stories]
    Path("seeds.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info("Successfully wrote %d verified seeds to seeds.json", len(manifest))
    return manifest
