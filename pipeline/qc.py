import json
import subprocess
from pathlib import Path
from typing import Dict, Any
from .models import QCResult, QCCheckResult
from .utils import run_ffprobe

class QualityControl:
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def run(self, video_path: Path, thumbnail_path: Path, metadata_path: Path, temp_dir: Path) -> QCResult:
        checks, errors, warnings = [], [], []
        if not video_path.exists():
            return QCResult(passed=False, score=0.0, checks=[QCCheckResult(name="file_exists", passed=False)], failures=["File missing"], warnings=[])

        try:
            probe = run_ffprobe([
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=width,height,r_frame_rate,duration",
                "-of", "json", str(video_path)
            ])
            vstream = probe["streams"][0]
            width, height = int(vstream["width"]), int(vstream["height"])
            num, den = map(int, vstream["r_frame_rate"].split('/'))
            fps = num / den
            duration = float(vstream["duration"])

            checks.append(QCCheckResult(name="resolution", passed=(width == 1080 and height == 1920), value=f"{width}x{height}"))
            checks.append(QCCheckResult(name="fps", passed=(abs(fps - 30.0) < 1.0), value=fps))
            checks.append(QCCheckResult(name="duration", passed=(self.config["qc"]["min_duration"] <= duration <= self.config["qc"]["max_duration"]), value=duration))
        except Exception as e:
            checks.append(QCCheckResult(name="ffprobe", passed=False, value=str(e)))
            errors.append(str(e))

        thumb_ok = thumbnail_path.exists()
        checks.append(QCCheckResult(name="thumbnail_exists", passed=thumb_ok))
        meta_ok = metadata_path.exists()
        checks.append(QCCheckResult(name="metadata_exists", passed=meta_ok))

        passed = all(c.passed for c in checks)
        score = sum(1 for c in checks if c.passed) / max(1, len(checks))
        return QCResult(passed=passed, score=score, checks=checks, failures=[c.name for c in checks if not c.passed], warnings=warnings)
