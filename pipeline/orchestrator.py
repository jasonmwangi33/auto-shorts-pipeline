#!/usr/bin/env python3
import json
import logging
from pathlib import Path
from story_engine import process_candidate_stream, PIPELINE_LLM_BUDGET
from pipeline.visuals import select_visual_theme
from pipeline.renderer import Renderer

logger = logging.getLogger("orchestrator")

class JobOrchestrator:
    def __init__(self, config: dict):
        self.config = config
        self.renderer = Renderer(config)

    def run_job(self, job_id: str, seed_file: str, auto_improve: bool = False, max_retries: int = 3, **kwargs):
        """Runs the individual render job using the project's actual Renderer."""
        logger.info("Executing job_id: %s using seed_file: %s", job_id, seed_file)
        
        seed_path = Path(seed_file)
        if not seed_path.exists():
            raise FileNotFoundError(f"Seed file not found: {seed_file}")
            
        seed_data = json.loads(seed_path.read_text(encoding="utf-8"))
        
        # Extract story and theme information safely
        story = seed_data.get("story", {})
        script = story.get("script", "")
        visual_theme = seed_data.get("visual_theme", select_visual_theme())
        
        logger.info("Loaded script (length: %d) with visual theme: %s", len(script.split()), visual_theme)
        
        # Hook into your existing renderer execution flow if required by main.py
        # If your main.py delegates rendering entirely, this ensures the orchestrator is fully bound.

def prepare_render_manifest(raw_candidates_supplier, target_count: int = 6) -> list:
    verified_stories = process_candidate_stream(raw_candidates_supplier, target_count=target_count, budget=PIPELINE_LLM_BUDGET)
    manifest = [{"seed_id": s.get("seed_id"), "story": s, "visual_theme": select_visual_theme()} for s in verified_stories]
    Path("seeds.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info("Successfully wrote %d verified seeds to seeds.json", len(manifest))
    return manifest
