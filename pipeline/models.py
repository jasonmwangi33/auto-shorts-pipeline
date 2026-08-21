from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum

class JobState(str, Enum):
    DISCOVERED = "discovered"
    RENDERING = "rendering"
    RENDERED = "rendered"
    APPROVED = "approved"
    QC_FAILED = "qc_failed"
    FAILED = "failed"

@dataclass
class AnalysisResult:
    duration: float
    fps: float = 30.0
    width: int = 1080
    height: int = 1920
    has_audio: bool = True

@dataclass
class EditPlan:
    target_duration: float
    subtitles_config: Dict[str, Any]
    narration_script: str
    narration_word_timings: List[Dict[str, Any]]

@dataclass
class RenderResult:
    output_path: str
    duration: float
    render_time: float
    file_size: int
    success: bool
    errors: List[str] = field(default_factory=list)
