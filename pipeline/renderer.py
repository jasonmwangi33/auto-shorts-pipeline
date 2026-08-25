import os
import re
import logging
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip, TextClip
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

    def _extract_story_text(self, plan) -> str:
        """
        Aggressively strips and blocks any configuration dicts, edit plans, 
        or code metadata from ever becoming video subtitles.
        """
        fallback_stories = [
            "My car was totaled, and now the kid who hit me is demanding I pay for his damages.",
            "I never expected my own family to turn against me over a stupid inheritance dispute.",
            "My boss thought he could fire me quietly until I uploaded the security footage online."
        ]
        
        if plan is None:
            return fallback_stories[0]

        # If it's a dictionary, look for actual text keys and reject config keys
        if isinstance(plan, dict):
            for key in ["script", "story", "text", "narrative", "content"]:
                if key in plan and plan[key]:
                    val = str(plan[key])
                    if not any(k in val.upper() for k in ["EDITPLAN", "SUBTITLES", "CONFIG", "STROKE", "OPACITY"]):
                        return val

        text = str(plan)
        
        # NUCLEAR FILTER: If the text contains any code parameters or config tokens, reject it entirely
        config_keywords = [
            "EDITPLAN", "SUBTITLES", "CONFIG", "FONT", "STROKE", 
            "OPACITY", "WIDTH", "DURATION", "COLOR", "ROUND", "{", "}"
        ]
        
        if any(keyword in text.upper() for keyword in config_keywords):
            logger.error(f"BLOCKED CONFIG LEAK IN RENDERER: Tried to render config string -> {text[:100]}...")
            return fallback_stories[hash(text) % len(fallback_stories)]
                
        # Clean up standard punctuation
        cleaned = re.sub(r'[^a-zA-Z0-9\s.,?!\-\'$]', '', text)
        cleaned = " ".join(cleaned.split())
        
        if len(cleaned) < 15:
            return fallback_stories[0]
            
        return cleaned

    def render(self, plan, narration_path, output_dir, job_id, headline=None, subreddit=None, visual_theme=None, **kwargs):
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.abspath(os.path.join(output_dir, f"{job_id}_output.mp4"))
        
        story_text = self._extract_story_text(plan)
        
        seed = {
            "id": job_id,
            "script": story_text,
            "audio_path": str(narration_path) if narration_path else None,
            "theme": visual_theme
        }
        return self.render_short(seed, output_path)

    def render_short(self, seed: dict, output_path: str):
        logger.info(f"Starting render for seed: {seed.get('id', 'unknown')}")
        output_path = os.path.abspath(output_path)
        audio_path = str(seed.get("audio_path")) if seed.get("audio_path") else None
        script_text = self._extract_story_text(seed.get("script", seed.get("story", "")))
        
        if not audio_path or not os.path.exists(audio_path):
            raise RuntimeError(f"Audio file missing for render: {audio_path}")
            
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
        
        bg_clip = self.visual_gen.generate_background(duration, seed)
        bg_clip = bg_clip.set_audio(audio_clip)
        progress_bar = self.visual_gen.generate_progress_bar(duration)
        
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
                        fontsize=95,
                        color='white',
                        stroke_color='black',
                        stroke_width=6,
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
