from typing import Dict, Any
from .models import FailureReport
from .config import deep_merge

class SelfImprovementEngine:
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def propose_config_patch(self, failure: FailureReport, current_config: Dict[str, Any]) -> Dict[str, Any]:
        return {}

    def should_retry(self, config: Dict[str, Any], attempts: int) -> bool:
        return attempts < self.config.get("self_improvement", {}).get("max_retries", 3)
