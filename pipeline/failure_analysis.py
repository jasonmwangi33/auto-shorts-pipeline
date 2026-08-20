from typing import Dict, Any
from .models import FailureReport, QCResult

class FailureAnalyzer:
    def analyze(self, job_id: str, stage: str, qc_result: QCResult, evidence: Dict[str, Any]) -> FailureReport:
        return FailureReport(
            job_id=job_id,
            stage=stage,
            failure_type=", ".join(qc_result.failures),
            severity="HARD_FAILURE" if not qc_result.passed else "NONE",
            evidence=evidence,
            probable_causes=["Parameter mismatch"],
            recommended_actions=["Retry with defaults"],
            configuration_changes={}
        )
