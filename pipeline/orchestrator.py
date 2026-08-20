import json
import subprocess
from pathlib import Path
from typing import Dict, Any
from .config import deep_merge
from .state import init_db, update_job_state, JobState
from .analysis import MediaAnalyzer
from .content_intelligence import ContentIntelligence
from .decision_engine import DecisionEngine
from .narration import NarrationEngine
from .renderer import Renderer
from .qc import QualityControl
from .failure_analysis import FailureAnalyzer
from .self_improvement import SelfImprovementEngine
from .utils import json_load, json_dump
from .models import AnalysisResult

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

        # 1. Narration & Timings
        print(f"[*] Generating Narration for Job {job_id}...")
        narration_engine = NarrationEngine(self.config)
        script, duration, word_timings, narration_path = narration_engine.generate(seed_data, tts_dir, job_id)
        print(f"[+] Narration generated: {duration:.2f}s")

        # 2. Decision & EditPlan
        headline = seed_data.get("headline", "Trending News")
        analysis = AnalysisResult(duration=duration, fps=30.0, width=1080, height=1920, has_audio=True)
        content_score = ContentIntelligence().score(script, {})
        decision = DecisionEngine(self.config)
        plan = decision.create_edit_plan(analysis, content_score, script, word_timings, headline=headline)

        # 3. Render
        print(f"[*] Rendering Video {job_id}...")
        renderer = Renderer(self.config)
        update_job_state(job_id, JobState.RENDERING)
        render_result = renderer.render(plan, narration_path, output_dir, job_id)

        if not render_result.success:
            print(f"[!] Render failed: {render_result.errors}")
            update_job_state(job_id, JobState.FAILED)
            return

        # 4. Thumbnail & Metadata Extraction
        thumbnail_path = output_dir / f"{job_id}_thumbnail.jpg"
        metadata_path = output_dir / f"{job_id}_metadata.json"
        
        subprocess.run(
            ["ffmpeg", "-y", "-ss", "1.0", "-i", render_result.output_path, "-frames:v", "1", "-q:v", "2", str(thumbnail_path)],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        metadata = {
            "title": headline[:60],
            "description": f"{script}\\n\\n#Shorts #Trending #News",
            "hashtags": ["#shorts", "#trending", "#news"]
        }
        json_dump(metadata, metadata_path)

        # 5. Quality Control & Manifest
        print(f"[*] Running QC on {job_id}...")
        qc = QualityControl(self.config)
        qc_result = qc.run(Path(render_result.output_path), thumbnail_path, metadata_path, output_dir)
        
        qc_manifest = {
            "job_id": job_id,
            "seed_index": seed_data.get("seed_index", 0),
            "passed": qc_result.passed,
            "output_file": str(render_result.output_path),
            "duration": duration,
            "score": qc_result.score
        }
        json_dump(qc_manifest, output_dir / f"{job_id}_qc.json")

        if qc_result.passed:
            print(f"[SUCCESS] Job {job_id} completed successfully (QC Score: {qc_result.score:.2f})!")
            update_job_state(job_id, JobState.APPROVED)
        else:
            print(f"[!] QC Failed for Job {job_id}: {qc_result.failures}")
            update_job_state(job_id, JobState.QC_FAILED)
