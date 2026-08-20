from pathlib import Path
from typing import Dict, Any
from .models import AnalysisResult

class MediaAnalyzer:
    def analyze(self, file_path: Path) -> AnalysisResult:
        return AnalysisResult(
            duration=35.0,
            fps=30.0,
            width=1080,
            height=1920,
            has_audio=True
        )
