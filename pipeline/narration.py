import asyncio
import edge_tts
import subprocess
import random
from pathlib import Path
from typing import Dict, Any, List, Tuple

class NarrationEngine:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tts_voice = config.get("narration", {}).get("tts_voice", "en-US-ChristopherNeural")
        self.tts_rate = config.get("narration", {}).get("tts_rate", "+12%")

    def build_script(self, seed_data: Dict[str, Any]) -> str:
        headline = seed_data.get("headline", "Viral Story")
        keywords = seed_data.get("keywords", [])
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split(',') if k.strip()]
        kw_str = ", ".join(keywords[:2]) if keywords else "the situation"

        # High-retention Reddit story narrative (~35-45s)
        hook = f"So, this happened yesterday and I honestly need to know if I was in the wrong. {headline}"
        story_setup = f"It all started when things escalated around {kw_str}. Everyone involved was acting completely unreasonable, and nobody wanted to take accountability."
        climax = "I decided to put my foot down and refuse to go along with their demands. Immediately, my phone started blowing up with messages calling me selfish and out of line."
        resolution = "Half the family is backing me up, but the other half says I took things way too far."
        outro = "Drop a comment and tell me: am I the one in the wrong here? Hit subscribe for part two!"

        return f"{hook} {story_setup} {climax} {resolution} {outro}"

    async def _generate_tts(self, script: str, output_path: Path) -> List[Dict[str, Any]]:
        delay = random.uniform(1.0, 8.0)
        print(f"[*] Staggering TTS request... waiting {delay:.2f}s")
        await asyncio.sleep(delay)

        communicate = edge_tts.Communicate(script, self.tts_voice, rate=self.tts_rate)
        word_events = []
        audio_chunks = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / 1e7
                dur = chunk["duration"] / 1e7
                word_events.append({"word": chunk["text"], "start": start, "end": start + dur})
        with open(output_path, "wb") as f:
            for data in audio_chunks:
                f.write(data)
        return word_events

    def generate(self, seed_data: Dict[str, Any], output_dir: Path, job_id: str) -> Tuple[str, float, List[Dict[str, Any]], Path]:
        script = self.build_script(seed_data)
        output_path = output_dir / f"{job_id}_narration.mp3"
        word_events = asyncio.run(self._generate_tts(script, output_path))

        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(output_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration = float(result.stdout.strip())
        return script, duration, word_events, output_path
