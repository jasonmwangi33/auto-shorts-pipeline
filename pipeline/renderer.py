import time
from pathlib import Path
from typing import Dict, Any
from moviepy.editor import AudioFileClip, CompositeVideoClip, CompositeAudioClip
from .models import EditPlan, RenderResult
from .visuals import VisualGenerator
from .subtitle import create_text_clip, apply_pop_animation
from .utils import make_temp_dir, cleanup_temp_dir

class Renderer:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.visual_generator = VisualGenerator(config)

    def render(self, plan: EditPlan, narration_audio_path: Path, output_dir: Path, job_id: str) -> RenderResult:
        start = time.time()
        temp_dir = make_temp_dir(prefix=f"render_{job_id}")
        try:
            duration = plan.target_duration
            bg_clip = self.visual_generator.generate_background(duration)
            progress_clip = self.visual_generator.generate_progress_bar(duration)

            hook_text = plan.hook_config.get("hook_text", "BREAKING NEWS")
            hook_clip = create_text_clip(
                hook_text.upper(),
                fontsize=plan.hook_config.get("font_size", 90),
                color=tuple(plan.hook_config.get("color", [255, 255, 0])),
                stroke_color=tuple(plan.hook_config.get("stroke_color", [0, 0, 0])),
                stroke_width=plan.hook_config.get("stroke_width", 6),
                bg_color=tuple(plan.hook_config.get("bg_color", [0, 0, 0])),
                bg_opacity=plan.hook_config.get("bg_opacity", 0.75),
                max_width=plan.hook_config.get("max_width", 1000)
            ).set_position(("center", plan.hook_config.get("position", 0.18)), relative=True).set_start(0).set_duration(plan.hook_config.get("duration", 3.0))

            subtitles = self._build_subtitles(plan, duration)
            audio_clip = AudioFileClip(str(narration_audio_path))
            all_clips = [bg_clip, progress_clip, hook_clip] + subtitles
            video = CompositeVideoClip(all_clips, size=(1080, 1920)).set_audio(audio_clip)

            output_path = output_dir / f"{job_id}_output.mp4"
            video.write_videofile(
                str(output_path),
                fps=self.config["render"].get("fps", 30),
                codec=self.config["render"].get("codec", "libx264"),
                audio_codec=self.config["render"].get("audio_codec", "aac"),
                preset=self.config["render"].get("preset", "ultrafast"),
                threads=self.config["render"].get("threads", 4),
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
            phrases = self._group_words(plan.narration_word_timings, plan.subtitles_config)
            for phrase_text, start, end in phrases:
                if start >= duration:
                    continue
                dur = min(end - start + 0.1, duration - start)
                if dur <= 0.05:
                    continue
                clip = create_text_clip(
                    phrase_text.upper(),
                    fontsize=plan.subtitles_config.get("font_size", 76),
                    color=tuple(plan.subtitles_config.get("color", [255, 255, 255])),
                    stroke_color=tuple(plan.subtitles_config.get("stroke_color", [0, 0, 0])),
                    stroke_width=plan.subtitles_config.get("stroke_width", 5),
                    bg_color=tuple(plan.subtitles_config.get("bg_color", [0, 0, 0])),
                    bg_opacity=plan.subtitles_config.get("bg_opacity", 0.6),
                    max_width=plan.subtitles_config.get("max_width", 950)
                )
                clip = apply_pop_animation(clip)
                clip = clip.set_start(start).set_duration(dur).set_position(("center", plan.subtitles_config.get("position", 0.70)), relative=True)
                subtitle_clips.append(clip)
        return subtitle_clips

    def _group_words(self, word_timings, subtitles_config):
        max_words = subtitles_config.get("max_words_per_phrase", 3)
        max_dur = subtitles_config.get("max_phrase_duration", 1.8)
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
