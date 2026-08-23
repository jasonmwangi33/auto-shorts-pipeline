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

    def render(self, plan: EditPlan, narration_audio_path: Path, output_dir: Path, job_id: str, headline: str = "", subreddit: str = "r/AmItheAsshole", visual_theme: str = "ASMR cooking") -> RenderResult:
        start = time.time()
        temp_dir = make_temp_dir(prefix=f"render_{job_id}")
        try:
            duration = plan.target_duration
            
            # 1. Hyper-Cut Background (Will raise error if no footage found)
            bg_clip = self.visual_generator.get_hypercut_background(duration, theme=visual_theme)
            
            # 2. Scrubber Progress Bar
            progress_clip = self.visual_generator.generate_progress_bar(duration)

            # 3. Reddit Stamp (Top 10%)
            reddit_stamp = generate_reddit_stamp_clip(headline, subreddit=subreddit, duration=3.5)

            # 4. Kinetic Subtitles (Max 2 words, True Center)
            subtitles = self._build_subtitles(plan, duration)

            # 5. Narration Audio
            audio_clip = AudioFileClip(str(narration_audio_path))
            
            # 6. Composite
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
            print(f"[!] RENDER CRASH: {e}")
            return RenderResult(output_path="", duration=0, render_time=0, file_size=0, success=False, errors=[str(e)])
        finally:
            cleanup_temp_dir(temp_dir)

    def _build_subtitles(self, plan: EditPlan, duration: float):
        subtitle_clips = []
        if plan.narration_word_timings:
            # Using exact word-boundary timing, packed into max 2 words
            phrases = self._group_words(plan.narration_word_timings, max_words=plan.subtitles_config.get("max_words_per_phrase", 2), max_dur=plan.subtitles_config.get("max_phrase_duration", 0.8))
            for phrase_text, start, end in phrases:
                if start >= duration:
                    continue
                dur = min(end - start + 0.1, duration - start)
                if dur <= 0.05:
                    continue
                clip = create_text_clip(
                    phrase_text.upper(),
                    fontsize=plan.subtitles_config.get("font_size", 85),
                    color=tuple(plan.subtitles_config.get("color", [255, 255, 255])),
                    stroke_color=tuple(plan.subtitles_config.get("stroke_color", [0, 0, 0])),
                    stroke_width=plan.subtitles_config.get("stroke_width", 7),
                    bg_color=None,
                    bg_opacity=0.0,
                    max_width=950
                )
                clip = apply_pop_animation(clip, scale_factor=0.25, pop_duration=0.10)
                # Positioned at true center
                clip = clip.set_start(start).set_duration(dur).set_position(("center", plan.subtitles_config.get("position", 0.50)), relative=True)
                subtitle_clips.append(clip)
        return subtitle_clips

    def _group_words(self, word_timings, max_words=2, max_dur=0.8):
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
