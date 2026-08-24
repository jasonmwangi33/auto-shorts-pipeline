#!/usr/bin/env python3
import json
import logging
from pathlib import Path
from story_engine import process_candidate_stream, PIPELINE_LLM_BUDGET
from pipeline.visuals import select_visual_theme
from pipeline.renderer import Renderer
from pipeline.models import EditPlan

logger = logging.getLogger("orchestrator")

class JobOrchestrator:
    def __init__(self, config: dict):
        self.config = config
        self.renderer = Renderer(config)

    def run_job(self, job_id: str, seed_file: str, auto_improve: bool = False, max_retries: int = 3, **kwargs):
        logger.info("Executing job_id: %s using seed_file: %s", job_id, seed_file)
        
        seed_path = Path(seed_file)
        if not seed_path.exists():
            raise FileNotFoundError(f"Seed file not found: {seed_file}")
            
        seed_data = json.loads(seed_path.read_text(encoding="utf-8"))
        
        headline = seed_data.get("headline", seed_data.get("topic", "Short Video"))
        subreddit = seed_data.get("subreddit", "r/AmItheAsshole")
        visual_theme = seed_data.get("visual_theme", select_visual_theme())
        
        # Look for narration audio generated in previous steps
        audio_path = Path("cache") / f"{job_id}_narration.mp3"
        if not audio_path.exists():
            mp3s = list(Path(".").glob("*.mp3")) + list(Path("cache").glob("*.mp3"))
            if mp3s:
                audio_path = mp3s[0]
            else:
                # Create a dummy silent audio or handle gracefully if missing
                audio_path = Path("cache") / "placeholder.mp3"
                audio_path.parent.mkdir(parents=True, exist_ok=True)

        output_dir = Path(".")
        
        # Build minimal valid word timings and script for EditPlan if not provided
        story = seed_data.get("story", seed_data)
        script_text = story.get("script", headline)
        word_timings = [{"word": w, "start": i * 0.3, "end": (i + 1) * 0.3} for i, w in enumerate(script_text.split())]
        
        plan = EditPlan(
            target_duration=max(15.0, len(word_timings) * 0.3),
            narration_script=script_text,
            narration_word_timings=word_timings,
            subtitles_config={"max_words_per_phrase": 2}
        )
        
        logger.info("Running Renderer to generate output video for job_id: %s", job_id)
        result = self.renderer.render(
            plan=plan,
            narration_audio_path=audio_path,
            output_dir=output_dir,
            job_id=job_id,
            headline=headline,
            subreddit=subreddit,
            visual_theme=visual_theme
        )
        
        if not result.success:
            raise RuntimeError(f"Renderer failed: {result.errors}")
        logger.info("Successfully generated video at: %s", result.output_path)

def prepare_render_manifest(raw_candidates_supplier, target_count: int = 6) -> list:
    verified_stories = process_candidate_stream(raw_candidates_supplier, target_count=target_count, budget=PIPELINE_LLM_BUDGET)
    manifest = [{"seed_id": s.get("seed_id"), "story": s, "visual_theme": select_visual_theme()} for s in verified_stories]
    Path("seeds.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info("Successfully wrote %d verified seeds to seeds.json", len(manifest))
    return manifest
