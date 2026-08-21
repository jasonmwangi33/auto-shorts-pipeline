import json
import os
import re
import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict

def sanitize_filename(name: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_-]', '_', name)

def json_load(path: Path) -> Dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def json_dump(data: Dict, path: Path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def make_temp_dir(prefix: str = "job") -> Path:
    return Path(tempfile.mkdtemp(prefix=f"{prefix}_"))

def cleanup_temp_dir(dir_path: Path):
    if dir_path.exists():
        shutil.rmtree(dir_path, ignore_errors=True)
