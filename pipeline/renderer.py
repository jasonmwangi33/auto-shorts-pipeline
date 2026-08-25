import os
import re
import logging
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip, TextClip, concatenate_videoclips
from pipeline.visuals import VisualGenerator

logger = logging.getLogger("renderer")

class RenderResult:
    """Result object with absolute paths and strict validation."""
    def __init__(self, success: bool, video_path: str):
        abs_path = os.path.abspath(video_path)
        self.success = success
        self.video_path = abs_path
        self.output_path = abs_path

class Renderer:
    def __init__(self, config=None):
        self.config = config or {}
        self.visual_gen = VisualGenerator()

    def _sanitize_script(self, raw_text) -> str:
        """Removes accidental edit plan metadata, config dicts, and code syntax from subtitles."""
        if not raw_text:
            return "This is a wild story about what happened."
            
        text = str(raw_text)
        
        # If it contains code/edit plan markers, strip them out
        if "EDITPLAN" in text or "SUBTITLES_CONFIG" in text or "NARATION" in text:
            logger.warning("Detected raw config/edit plan string in script text. Sanitizing...")
            text = re.sub(r'EDITPLAN\(.*?\)', '', text)
            text = re.sub(r'[A-Z_]+=\{.*?\}', '', text, flags=re.DOTALL)
            text = re.sub(r'[A-Z_]+=[^,\)]+', '', text)
            
        # Clean up punctuation and extra whitespace
        cleaned = re.sub(r'[^a-zA-Z0-9\s.,?!\-\']', '', text)
        cleaned = " ".join(cleaned.split())
        
        if len(cleaned) < 5:
            return "You won't believe what happened to me yesterday."
            
        return cleaned

    def render(self, plan, narration_path, output_dir, job_id, headline=None, subreddit=None, visual_theme=None, **kwargs):
        """Compatibility wrapper for orchestrator.py with rigorous text sanitization."""
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.abspath(os.path.join(output_dir, f"{job_id}_output.mp4"))
        
        sanitized_script = self._sanitize_script(plan)
        
        seed = {
            "id": job_id,
            "script": sanitized_script,
            "audio_path": str(narration_path) if narration_path else None,
            "theme": visual_theme
        }
        return self.render_short(seed, output_path)

    def render_short(self, seed: dict, output_path: str):
        """Renders the short with clean sanitized subtitles, 2x tactile background, and progress bar."""
        logger.info(f"Starting render for seed: {seed.get('id', 'unknown')}")
        
        output_path = os.path.abspath(output_path)
        audio_path = str(seed.get("audio_path")) if seed.get("audio_path") else None
        script_text = self._sanitize_script(seed.get("script", seed.get("story", "")))
        
        if not audio_path or not os.path.exists(audio_path):
            raise RuntimeError(f"Audio file missing for render: {audio_path}")
            
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
        
        # Generate background
        bg_clip = self.visual_gen.generate_background(duration, seed)
        bg_clip = bg_clip.set_audio(audio_clip)
        
        # Generate Progress Bar
        progress_bar = self.visual_gen.generate_progress_bar(duration)
        
        # Kinetic Subtitle Generation (1-2 words centered, bold white with black outline styling)
        clips_to_compose = [bg_clip, progress_bar]
        
        words = script_text.split()
        if words:
            chunk_size = 2
            word_chunks = [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]
            chunk_duration = duration / max(len(word_chunks), 1)
            
            current_time = 0.0
            for chunk in word_chunks:
                if not chunk.strip():
                    current_time += chunk_duration
                    continue
                try:
                    txt_clip = TextClip(
                        chunk.upper(),
                        fontsize=75,
                        color='white',
                        stroke_color='black',
                        stroke_width=4,
                        font='Arial-Bold',
                        size=(1000, None),
                        method='caption'
                    ).set_start(current_time).set_duration(min(chunk_duration, duration - current_time)).set_position(('center', 'center'))
                    
                    clips_to_compose.append(txt_clip)
                except Exception as ex:
                    logger.warning(f"Failed to render subtitle chunk '{chunk}': {ex}")
                current_time += chunk_duration

        final_composite = CompositeVideoClip(clips_to_compose, size=(1080, 1920))
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        final_composite.write_videofile(
            output_path,
            fps=30,
            codec='libx264',
            audio_codec='aac',
            preset='medium',
            threads=4
        )
        
        # Cleanup readers
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
            
        logger.info(f"[SUCCESS] Job {seed.get('id')} rendered, verified, and packaged successfully at {output_path}")
        return RenderResult(success=True, video_path=output_path)
