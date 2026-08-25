import os
import re
import logging
from moviepy.editor import AudioFileClip, CompositeVideoClip, TextClip
from pipeline.visuals import VisualGenerator

logger = logging.getLogger("renderer")

class RenderResult:
    def __init__(self, success: bool, video_path: str):
        abs_path = os.path.abspath(video_path)
        self.success = success
        self.video_path = abs_path
        self.output_path = abs_path

class Renderer:
    def __init__(self, config=None):
        self.config = config or {}
        self.visual_gen = VisualGenerator()

    def _resolve_bold_font(self) -> str:
        """Determines reliable bold font identifier on Windows/Linux."""
        windows_impact = "C:\\Windows\\Fonts\\impact.ttf"
        if os.path.exists(windows_impact):
            return windows_impact
        return "Impact"

    def _validate_story_text(self, raw_input) -> str:
        """
        Enforces strict string type contract at the subtitle boundary.
        Fails loudly on non-string or serialized object inputs without using str() fallback.
        """
        if raw_input is None:
            raise TypeError("Subtitle text boundary received None instead of str.")
            
        if isinstance(raw_input, str):
            text = raw_input.strip()
            # Explicitly guard against serialized dataclass/repr dumps
            if text.startswith("EditPlan(") or "EDITPLAN(" in text.upper():
                raise TypeError("Data contract violation: Received serialized EditPlan string instead of raw story text.")
            if not text:
                raise ValueError("Subtitle text boundary received an empty string.")
            return text
            
        # If an upstream object was mistakenly passed, reject it cleanly
        raise TypeError(f"Data contract violation: Subtitle text must be a valid str, got {type(raw_input).__name__}")

    def _build_subtitle_clips(self, script_text: str, duration: float, word_timings: list = None) -> list:
        """
        Constructs 1-2 word kinetic subtitle TextClips strictly ordered in time.
        Prefers actual Edge-TTS word-boundary events when available.
        """
        font_target = self._resolve_bold_font()
        clips = []

        # Path A: Using actual Edge-TTS word-boundary event data
        if word_timings and isinstance(word_timings, list) and len(word_timings) > 0:
            logger.info(f"Building kinetic subtitles from {len(word_timings)} Edge-TTS word boundaries.")
            
            # Clean and normalize timing items
            clean_events = []
            for item in word_timings:
                w = item.get("word") or item.get("text") or ""
                w = re.sub(r'[^a-zA-Z0-9\s.,?!\-\'$]', '', str(w)).strip()
                if not w:
                    continue
                start_s = float(item.get("start", item.get("start_ms", 0)))
                end_s = float(item.get("end", item.get("end_ms", 0)))
                # Convert ms to seconds if values are in milliseconds
                if start_s > 1000 and duration < 300:
                    start_s /= 1000.0
                    end_s /= 1000.0
                clean_events.append({"word": w, "start": start_s, "end": max(end_s, start_s + 0.1)})

            # Group into 1-2 words preserving chronological order
            idx = 0
            while idx < len(clean_events):
                group = clean_events[idx:idx + 2]
                text_chunk = " ".join([e["word"] for e in group]).upper()
                start_time = group[0]["start"]
                end_time = group[-1]["end"]
                clip_duration = max(0.15, end_time - start_time)
                
                if start_time < duration:
                    try:
                        txt_clip = TextClip(
                            text_chunk,
                            fontsize=110,
                            color='white',
                            stroke_color='black',
                            stroke_width=8,
                            font=font_target,
                            size=(1000, None),
                            method='caption'
                        ).set_start(start_time).set_duration(min(clip_duration, duration - start_time)).set_position(('center', 'center'))
                        clips.append(txt_clip)
                    except Exception as ex:
                        logger.warning(f"Failed rendering TTS word chunk '{text_chunk}': {ex}")
                idx += len(group)

            if clips:
                return clips

        # Path B: Controlled fallback if word-boundary events are unavailable
        words = script_text.split()
        if not words:
            return clips

        chunk_size = 2
        word_chunks = [" ".join(words[i:i+chunk_size]).upper() for i in range(0, len(words), chunk_size)]
        chunk_duration = duration / max(len(word_chunks), 1)
        
        current_time = 0.0
        for chunk in word_chunks:
            if not chunk.strip():
                current_time += chunk_duration
                continue
            try:
                txt_clip = TextClip(
                    chunk,
                    fontsize=110,
                    color='white',
                    stroke_color='black',
                    stroke_width=8,
                    font=font_target,
                    size=(1000, None),
                    method='caption'
                ).set_start(current_time).set_duration(min(chunk_duration, duration - current_time)).set_position(('center', 'center'))
                clips.append(txt_clip)
            except Exception as ex:
                logger.warning(f"Failed rendering subtitle chunk '{chunk}': {ex}")
            current_time += chunk_duration

        return clips

    def render(self, script_or_plan, narration_path, output_dir, job_id, headline=None, subreddit=None, visual_theme=None, word_timings=None, **kwargs):
        """
        Renderer entry point. Enforces explicit text extraction upstream.
        """
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.abspath(os.path.join(output_dir, f"{job_id}_output.mp4"))
        
        # Explicit upstream string extraction if an EditPlan or dict was provided
        if hasattr(script_or_plan, "script") and isinstance(script_or_plan.script, str):
            extracted_text = script_or_plan.script
        elif isinstance(script_or_plan, dict) and "script" in script_or_plan and isinstance(script_or_plan["script"], str):
            extracted_text = script_or_plan["script"]
        elif isinstance(script_or_plan, str):
            extracted_text = script_or_plan
        else:
            raise TypeError(f"Renderer requires a valid string script or an object with a .script string, got {type(script_or_plan).__name__}")

        validated_script = self._validate_story_text(extracted_text)
        
        seed = {
            "id": job_id,
            "script": validated_script,
            "audio_path": str(narration_path) if narration_path else None,
            "theme": visual_theme,
            "word_timings": word_timings or kwargs.get("subtitles") or kwargs.get("words")
        }
        return self.render_short(seed, output_path)

    def render_short(self, seed: dict, output_path: str):
        logger.info(f"Starting render for seed: {seed.get('id', 'unknown')}")
        output_path = os.path.abspath(output_path)
        audio_path = str(seed.get("audio_path")) if seed.get("audio_path") else None
        
        script_text = self._validate_story_text(seed.get("script", seed.get("story", "")))
        word_timings = seed.get("word_timings")
        
        if not audio_path or not os.path.exists(audio_path):
            raise RuntimeError(f"Audio file missing for render: {audio_path}")
            
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
        
        bg_clip = self.visual_gen.generate_background(duration, seed)
        bg_clip = bg_clip.set_audio(audio_clip)
        progress_bar = self.visual_gen.generate_progress_bar(duration)
        
        subtitle_clips = self._build_subtitle_clips(script_text, duration, word_timings)
        clips_to_compose = [bg_clip, progress_bar] + subtitle_clips

        final_composite = CompositeVideoClip(clips_to_compose, size=(1080, 1920))
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        final_composite.write_videofile(
            output_path, fps=30, codec='libx264', audio_codec='aac', preset='medium', threads=4
        )
        
        audio_clip.close()
        bg_clip.close()
        if hasattr(bg_clip, 'source_readers'):
            for reader in bg_clip.source_readers:
                try: reader.close()
                except: pass

        if hasattr(os, 'sync'):
            os.sync()
            
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise RuntimeError(f"Render validation failed: Output video at {output_path} is missing or empty.")
            
        return RenderResult(success=True, video_path=output_path)
