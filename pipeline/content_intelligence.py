from typing import Dict, Any
from .models import ContentScore

class ContentIntelligence:
    def score(self, script: str, analysis: Dict[str, Any]) -> ContentScore:
        score = ContentScore()
        score.hook_strength = 0.9
        score.clarity = 0.85
        score.information_density = 0.8
        score.pacing = 0.85
        score.overall = 0.85
        return score
