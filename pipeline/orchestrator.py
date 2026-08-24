#!/usr/bin/env python3
import json
import logging
import subprocess
import sys
from pathlib import Path
from story_engine import process_candidate_stream, PIPELINE_LLM_BUDGET
from pipeline.visuals import select_visual_theme

logger = logging.getLogger("orchestrator")

class JobOrchestrator:
    def __init__(self, config: dict):
        self.config = config

    def run_job(self, job_id: str, seed_file: str, auto_improve: bool = False, max_retries: int = 3, **kwargs):
        logger.info("Executing job_id: %s using seed_file: %s", job_id, seed_file)
        
        seed_path = Path(seed_file)
        if not seed_path.exists():
            raise FileNotFoundError(f"Seed file not found: {seed_file}")
            
        seed_data = json.loads(seed_path.read_text(encoding="utf-8"))
        
        # If main.py expects to run the core pipeline script for this seed, 
        # pass execution down to the underlying rendering module or let main.py handle it.
        logger.info("Orchestrator ready for seed parameters: %s", list(seed_data.keys()))

def prepare_render_manifest(raw_candidates_supplier, target_count: int = 6) -> list:
    verified_stories = process_candidate_stream(raw_candidates_supplier, target_count=target_count, budget=PIPELINE_LLM_BUDGET)
    manifest = [{"seed_id": s.get("seed_id"), "story": s, "visual_theme": select_visual_theme()} for s in verified_stories]
    Path("seeds.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info("Successfully wrote %d verified seeds to seeds.json", len(manifest))
    return manifest
