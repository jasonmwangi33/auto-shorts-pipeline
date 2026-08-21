import time
from pathlib import Path
from typing import Dict, Any
from moviepy.editor import AudioFileClip, CompositeVideoClip
from .models import EditPlan, RenderResult
from .visuals import VisualGenerator
from .reddit_card import generate_reddit_stamp_clip
from .subtitle import create_text_clip, apply_pop_animation
from .utils import make_temp_dir, cleanup_temp_dir

class Renderer:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.visual_generator = VisualGenerator(config)

    def render(self, plan: EditPlan, narration_audio_path: Path, output_dir: Path, job_id: str, headline: str = "", subreddit: str = "r/AmItheAsshole") -> RenderResult:
        start = time.time()
        temp_dir = make_temp_dir(prefix=f"render_{job_id}")
        try:
            duration = plan.target_duration
            
            # 1. Background Video Layer (Web gameplay / ASMR food slice)
            bg_clip = self.visual_generator.get_background_clip(duration)
            
            # 2. Scrubber Progress Bar
            progress_clip = self.visual_generator.generate_progress_bar(duration)

            # 3. Reddit Stamp Overlay Card (0 to 3.5s)
            reddit_stamp = generate_reddit_stamp_clip(headline, subreddit=subreddit, duration=3.5)

            # 4. Kinetic Pop Subtitles
            subtitles = self._build_subtitles(plan, duration)

            # 5. Narration Audio
            audio_clip = AudioFileClip(str(narration_audio_path))
            
            # 6. Composite & Compile
            all_clips = [bg_clip, progress_clip, reddit_stamp] + subtitles
            video = CompositeVideoClip(all_clips, size=(1080, 1920)).set_audio(audio_clip)

            output_path = output_dir / f"{job_id}_output.mp4"
            video.write_videofile(
                str(output_path),
                fps=30,
                codec="libx264",
                audio_codec="aac",
                preset="ultrafast",
                threads=4,
                logger=None
            )
            render_time = time.time() - start
            file_size = output_path.stat().st_size

            video.close()
            audio_clip.close()

            return RenderResult(
                output_path=str(output_path),
                duration=duration,
                render_time=render_time,
                file_size=file_size,
                success=True
            )
        except Exception as e:
            return RenderResult(output_path="", duration=0, render_time=0, file_size=0, success=False, errors=[str(e)])
        finally:
            cleanup_temp_dir(temp_dir)

    def _build_subtitles(self, plan: EditPlan, duration: float):
        subtitle_clips = []
        if plan.narration_word_timings:
            phrases = self._group_words(plan.narration_word_timings, max_words=3, max_dur=1.6)
            for phrase_text, start, end in phrases:
                if start >= duration:
                    continue
                dur = min(end - start + 0.1, duration - start)
                if dur <= 0.05:
                    continue
                clip = create_text_clip(
                    phrase_text.upper(),
                    fontsize=80,
                    color=(255, 255, 255),
                    stroke_color=(0, 0, 0),
                    stroke_width=6,
                    bg_color=(0, 0, 0),
                    bg_opacity=0.65,
                    max_width=950
                )
                clip = apply_pop_animation(clip, scale_factor=0.25, pop_duration=0.15)
                clip = clip.set_start(start).set_duration(dur).set_position(("center", 0.68), relative=True)
                subtitle_clips.append(clip)
        return subtitle_clips

    def _group_words(self, word_timings, max_words=3, max_dur=1.6):
        phrases, cur_words, cur_start, cur_end = [], [], None, None
        for item in word_timings:
            word, start, end = item["word"], item["start"], item["end"]
            if cur_start is None:
                cur_start = start
            cur_words.append(word)
            cur_end = end
            if len(cur_words) >= max_words or (cur_end - cur_start) >= max_dur:
                phrases.append((" ".join(cur_words), cur_start, cur_end))
                cur_words, cur_start, cur_end = [], None, None
        if cur_words:
            phrases.append((" ".join(cur_words), cur_start, cur_end))
        return phrases
