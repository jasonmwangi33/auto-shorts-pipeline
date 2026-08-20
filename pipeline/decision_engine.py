from typing import Dict, Any
from .models import AnalysisResult, ContentScore, EditPlan

class DecisionEngine:
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def create_edit_plan(self, analysis: AnalysisResult, content_score: ContentScore, narration_script: str, word_timings, headline: str = "") -> EditPlan:
        hook_cfg = dict(self.config["hook"])
        hook_cfg["hook_text"] = headline[:50] + ("..." if len(headline) > 50 else "")
        return EditPlan(
            target_duration=analysis.duration,
            crop_strategy="center",
            crop_position=(0.5, 0.5),
            subtitles_enabled=True,
            subtitles_config=self.config["subtitles"],
            hook_config=hook_cfg,
            visuals_config=self.config["visuals"],
            audio_config=self.config["audio"],
            narration_script=narration_script,
            narration_word_timings=word_timings
        )
