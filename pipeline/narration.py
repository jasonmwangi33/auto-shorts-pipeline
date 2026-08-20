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
        self.tts_rate = config.get("narration", {}).get("tts_rate", "+10%")

    def build_script(self, seed_data: Dict[str, Any]) -> str:
        headline = seed_data.get("headline", "Trending News")
        topic = seed_data.get("topic", headline)
        keywords = seed_data.get("keywords", [])
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split(',') if k.strip()]
        kw_str = ", ".join(keywords[:3]) if keywords else "the most critical details"

        hook = f"Here is exactly why {headline} is going completely viral right now."
        context = f"The situation surrounding {topic} has been developing rapidly over the last 24 hours, and it is catching everyone by surprise."
        details = f"When you look closely at the data, especially regarding {kw_str}, it becomes clear that experts are monitoring this very closely. This is not just a minor update; it could shift our entire perspective on the subject."
        implications = f"If these current trends continue, we are going to see massive changes in how this is handled moving forward. You absolutely do not want to be left behind as this story unfolds."
        outro = "Make sure to hit the subscribe button for daily updates, and let me know what you think in the comments below!"
        
        return f"{hook} {context} {details} {implications} {outro}"

    async def _generate_tts(self, script: str, output_path: Path) -> List[Dict[str, Any]]:
        # THE FIX: Tell the cloud computer to wait between 1 and 15 seconds randomly 
        # so we don't trigger Microsoft's spam filters
        delay = random.uniform(1.0, 15.0)
        print(f"[*] Staggering API request... waiting {delay:.2f} seconds.")
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
