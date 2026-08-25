import json
import random
import subprocess
from pathlib import Path
from typing import Dict, Any
from .state import init_db, update_job_state, JobState
from .narration import NarrationEngine
from .renderer import Renderer
from .utils import json_load, json_dump
from .models import EditPlan

# High-retention visual themes independent of the narrative
VISUAL_THEMES = [
    "ASMR cooking", 
    "satisfying food preparation", 
    "kinetic sand", 
    "satisfying machinery", 
    "satisfying cleaning"
]

class JobOrchestrator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        init_db()

    def run_job(self, job_id: str, seed_file: str, auto_improve: bool = False, max_retries: int = 3):
        seed_path = Path(seed_file)
        if not seed_path.exists():
            print(f"[!] Seed file not found: {seed_file}")
            return

        seed_data = json_load(seed_path)
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        tts_dir = Path("data/tts_cache")
        tts_dir.mkdir(parents=True, exist_ok=True)

        update_job_state(job_id, JobState.DISCOVERED)

        headline = seed_data.get("headline", "Trending Story")
        subreddit = seed_data.get("subreddit", seed_data.get("topic", "r/AmItheAsshole"))
        
        # Select an independent visual theme
        selected_theme = random.choice(VISUAL_THEMES)

        print(f"[*] Generating Narration for Job {job_id}...")
        narration_engine = NarrationEngine(self.config)
        script, duration, word_timings, narration_path = narration_engine.generate(seed_data, tts_dir, job_id)
        
        plan = EditPlan(
            target_duration=duration,
            subtitles_config=self.config["subtitles"],
            narration_script=script,
            narration_word_timings=word_timings
        )

        print(f"[*] Rendering {job_id} with independent visual theme: '{selected_theme}'")
        renderer = Renderer(self.config)
        update_job_state(job_id, JobState.RENDERING)
                # Extract script string cleanly from plan object before renderer boundary
        plan_script = getattr(plan, 'script', getattr(plan, 'story', getattr(plan, 'text', str(plan))))
        render_result = renderer.render(
            plan.narration_script, narration_path, output_dir, job_id, headline=headline, subreddit=subreddit, visual_theme=selected_theme, word_timings=plan.narration_word_timings)

        if not render_result.success:
            print(f"[!] Render fatally failed. Skipping QC and artifacts.")
            update_job_state(job_id, JobState.FAILED)
            
            # Write a failed QC manifest so the router knows to skip it
            qc_manifest = {"job_id": job_id, "seed_index": seed_data.get("seed_index", 0), "passed": False, "score": 0.0}
            json_dump(qc_manifest, output_dir / f"{job_id}_qc.json")
            return

        thumbnail_path = output_dir / f"{job_id}_thumbnail.jpg"
        metadata_path = output_dir / f"{job_id}_metadata.json"
        
        subprocess.run(
            ["ffmpeg", "-y", "-ss", "2.0", "-i", render_result.output_path, "-frames:v", "1", "-q:v", "2", str(thumbnail_path)],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        metadata = {
            "title": headline[:70],
            "description": f"{script}\n\n#Shorts #RedditStories #AITA #Viral",
            "hashtags": ["#shorts", "#redditstories", "#aita"]
        }
        json_dump(metadata, metadata_path)

        qc_manifest = {
            "job_id": job_id,
            "seed_index": seed_data.get("seed_index", 0),
            "passed": True,
            "output_file": str(render_result.output_path),
            "duration": duration,
            "score": 1.0
        }
        json_dump(qc_manifest, output_dir / f"{job_id}_qc.json")
        print(f"[SUCCESS] Job {job_id} rendered and packaged successfully!")
        update_job_state(job_id, JobState.APPROVED)

