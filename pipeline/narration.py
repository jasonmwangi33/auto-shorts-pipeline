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
        headline = seed_data.get("headline", "Relatable thought")
        
        hook = f"Okay, tell me if I am the only one who does this, or if we all just live the exact same life. {headline}"
        body = "I was literally just thinking about this the other day. It is so crazy how we all have these universal experiences but nobody ever talks about them out loud. It makes you realize how similar human brains actually are."
        resolution = "The more you think about it, the more it messes with your head. It is one of those things that once you notice it, you can never un-notice it."
        outro = "Drop a comment and let me know if you do this too, and hit subscribe for more relatable thoughts!"

        return f"{hook} {body} {resolution} {outro}"

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
