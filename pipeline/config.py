import json
import copy
from pathlib import Path
from typing import Any, Dict

DEFAULT_CONFIG = {
    "video": {
        "target_width": 1080,
        "target_height": 1920,
        "target_fps": 30,
        "min_duration": 25.0,
        "target_duration": 40.0,
        "max_duration": 60.0
    },
    "audio": {
        "voice_volume": 1.0,
        "ambient_volume": 0.1,
        "fade_duration": 0.2
    },
    "subtitles": {
        "font_size": 85,
        "color": [255, 255, 255],
        "stroke_color": [0, 0, 0],
        "stroke_width": 7,
        "bg_color": None, 
        "bg_opacity": 0.0,
        "position": 0.50, # Moved to true center
        "max_width": 950,
        "max_words_per_phrase": 2, # Strict 1-2 word limit
        "max_phrase_duration": 0.8
    },
    "narration": {
        "tts_voice": "en-US-ChristopherNeural",
        "tts_rate": "+12%"
    }
}

def load_config(path: str = "config.json") -> Dict[str, Any]:
    config_path = Path(path)
    config = copy.deepcopy(DEFAULT_CONFIG)
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            user_config = json.load(f)
            config.update(user_config)
    return config
