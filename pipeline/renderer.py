import os
import logging
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip, TextClip, concatenate_videoclips
from pipeline.visuals import VisualGenerator

logger = logging.getLogger("renderer")

class RenderResult:
    """Result object to satisfy orchestrator.py expecting .success and .output_path attributes."""
    def __init__(self, success: bool, video_path: str):
        self.success = success
        self.video_path = video_path
        self.output_path = video_path  # Satisfy orchestrator.py expectation

class Renderer:
    def __init__(self, config=None):
        self.config = config or {}
        self.visual_gen = VisualGenerator()

    def render(self, plan, narration_path, output_dir, job_id, headline=None, subreddit=None, visual_theme=None, **kwargs):
        """Compatibility wrapper for orchestrator.py returning a RenderResult object."""
        output_path = os.path.join(output_dir, f"{job_id}.mp4")
        seed = {
            "id": job_id,
            "script": plan if isinstance(plan, str) else str(plan),
            "audio_path": str(narration_path) if narration_path else None,
            "theme": visual_theme
        }
        return self.render_short(seed, output_path)

    def render_short(self, seed: dict, output_path: str):
        """Renders the short with fast-paced 2x background, clear audio, and centered bold kinetic captions (1-2 words)."""
        logger.info(f"Starting render for seed: {seed.get('id', 'unknown')}")
        
        audio_path = str(seed.get("audio_path")) if seed.get("audio_path") else None
        script_text = seed.get("script", seed.get("story", "This is a story."))
        
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
            chunk_duration = duration / len(word_chunks)
            
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
                
        logger.info(f"Successfully rendered video to {output_path}")
        return RenderResult(success=True, video_path=output_path)
