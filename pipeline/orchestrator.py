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

    def run_job(self, job_id: str, seed_file: str, auto_improve: bool = False, max_retries: int = 3, **kwargs):
        logger.info("Executing job_id: %s using seed_file: %s", job_id, seed_file)
        
        seed_path = Path(seed_file)
        if not seed_path.exists():
            raise FileNotFoundError(f"Seed file not found: {seed_file}")
            
        seed_data = json.loads(seed_path.read_text(encoding="utf-8"))
        logger.info("Raw seed_data keys found: %s", list(seed_data.keys()) if isinstance(seed_data, dict) else type(seed_data))
        
        # Deep recursive search for any string that looks like a script or text content
        def find_text(obj):
            if isinstance(obj, str) and len(obj.split()) > 10:
                return obj
            if isinstance(obj, dict):
                for k, v in obj.items():
                    res = find_text(v)
                    if res: return res
            elif isinstance(obj, list):
                for item in obj:
                    res = find_text(item)
                    if res: return res
            return ""

        script = find_text(seed_data)
        if not script:
            # Fallback to stringifying the story or seed data if text search fails
            script = seed_data.get("script", seed_data.get("text", str(seed_data)))

        logger.info("Extracted script length: %d words", len(script.split()))
        
        if not script.strip():
            raise ValueError(f"CRITICAL: Could not extract script from job context. Data was: {seed_data}")

def prepare_render_manifest(raw_candidates_supplier, target_count: int = 6) -> list:
    verified_stories = process_candidate_stream(raw_candidates_supplier, target_count=target_count, budget=PIPELINE_LLM_BUDGET)
    manifest = [{"seed_id": s.get("seed_id"), "story": s, "visual_theme": select_visual_theme()} for s in verified_stories]
    Path("seeds.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info("Successfully wrote %d verified seeds to seeds.json", len(manifest))
    return manifest
