from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum

class JobState(str, Enum):
    DISCOVERED = "discovered"
    ANALYZING = "analyzing"
    ANALYZED = "analyzed"
    PLANNING = "planning"
    RENDERING = "rendering"
    RENDERED = "rendered"
    QC_RUNNING = "qc_running"
    QC_FAILED = "qc_failed"
    IMPROVING = "improving"
    APPROVED = "approved"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"

@dataclass
class AnalysisResult:
    duration: float
    fps: float
    width: int
    height: int
    audio_duration: Optional[float] = None
    silence_segments: List[Tuple[float, float]] = field(default_factory=list)
    speech_segments: List[Tuple[float, float]] = field(default_factory=list)
    scene_boundaries: List[float] = field(default_factory=list)
    has_audio: bool = False
    brightness_mean: float = 128.0
    contrast_mean: float = 50.0
    raw: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ContentScore:
    hook_strength: float = 0.0
    clarity: float = 0.0
    information_density: float = 0.0
    pacing: float = 0.0
    novelty: float = 0.0
    curiosity: float = 0.0
    emotional_intensity: float = 0.0
    narrative_progression: float = 0.0
    payoff: float = 0.0
    ending_strength: float = 0.0
    repetition: float = 0.0
    filler: float = 0.0
    overall: float = 0.0

@dataclass
class EditPlan:
    target_duration: float
    crop_strategy: str
    crop_position: Tuple[float, float]
    subtitles_enabled: bool
    subtitles_config: Dict[str, Any]
    hook_config: Dict[str, Any]
    visuals_config: Dict[str, Any]
    audio_config: Dict[str, Any]
    narration_script: Optional[str] = None
    narration_word_timings: Optional[List[Dict[str, Any]]] = None

@dataclass
class RenderResult:
    output_path: str
    duration: float
    render_time: float
    file_size: int
    success: bool
    errors: List[str] = field(default_factory=list)

@dataclass
class QCCheckResult:
    name: str
    passed: bool
    value: Any = None
    severity: str = "HARD_FAILURE"

@dataclass
class QCResult:
    passed: bool
    score: float
    checks: List[QCCheckResult]
    failures: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

@dataclass
class FailureReport:
    job_id: str
    stage: str
    failure_type: str
    severity: str
    evidence: Dict[str, Any]
    probable_causes: List[str]
    recommended_actions: List[str]
    configuration_changes: Dict[str, Any]
