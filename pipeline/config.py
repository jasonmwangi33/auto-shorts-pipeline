import json
import copy
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_CONFIG = {
    "video": {
        "target_width": 1080,
        "target_height": 1920,
        "target_fps": 30,
        "min_duration": 15.0,
        "target_duration": 40.0,
        "max_duration": 60.0
    },
    "audio": {
        "silence_threshold": -40.0,
        "min_silence_duration": 0.5,
        "voice_volume": 1.0,
        "ambient_volume": 0.1,
        "fade_duration": 0.3
    },
    "subtitles": {
        "font_size": 76,
        "color": [255, 255, 255],
        "stroke_color": [0, 0, 0],
        "stroke_width": 5,
        "bg_color": [0, 0, 0],
        "bg_opacity": 0.6,
        "position": 0.70,
        "max_width": 950,
        "max_words_per_phrase": 4,
        "max_phrase_duration": 2.0,
        "animation": "pop"
    },
    "hook": {
        "duration": 3.0,
        "font_size": 90,
        "color": [255, 255, 0],
        "stroke_color": [0, 0, 0],
        "stroke_width": 6,
        "bg_color": [0, 0, 0],
        "bg_opacity": 0.75,
        "position": 0.18,
        "max_width": 1000
    },
    "visuals": {
        "crop_mode": "center",
        "background": "gradient",
        "motion_intensity": 0.10,
        "floating_shapes": True
    },
    "render": {
        "codec": "libx264",
        "audio_codec": "aac",
        "preset": "ultrafast",
        "threads": 4,
        "bitrate": "2500k",
        "fps": 30
    },
    "qc": {
        "min_duration": 15.0,
        "max_duration": 60.0,
        "required_width": 1080,
        "required_height": 1920,
        "required_fps": 30,
        "audio_duration_tolerance": 0.5,
        "black_frame_threshold": 5,
        "min_brightness": 5,
        "max_brightness": 250,
        "check_hook": True
    },
    "self_improvement": {
        "max_retries": 3,
        "max_auto_patches": 2,
        "max_experiments": 2,
        "max_render_time": 600,
        "max_job_time": 1800,
        "patch_strategy": "config_first"
    },
    "narration": {
        "target_duration_range": [30.0, 50.0],
        "tts_voice": "en-US-ChristopherNeural",
        "tts_rate": "+10%"
    }
}

def load_config(path: str = "config.json") -> Dict[str, Any]:
    config_path = Path(path)
    config = copy.deepcopy(DEFAULT_CONFIG)
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            user_config = json.load(f)
            config = deep_merge(config, user_config)
    return config

def save_config(config: Dict[str, Any], path: str = "config.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

def deep_merge(base: Dict, override: Dict) -> Dict:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result
