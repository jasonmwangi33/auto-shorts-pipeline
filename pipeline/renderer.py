import logging
from moviepy.editor import AudioFileClip, CompositeVideoClip, TextClip

logger = logging.getLogger("renderer")

def render_short(script: str, audio_path: str, background_clip, output_path: str):
    logger.info("Starting production render sequence")
    
    audio_clip = AudioFileClip(audio_path)
    duration = audio_clip.duration
    bg_clip = background_clip.subclip(0, duration)
    
    # Restored subtitle configuration
    max_words_per_phrase = 2
    subtitle_alignment = "center"
    story_card_vertical_position = "upper"
    
    # In a full run, your TTS/word-boundary generator parses `script` here
    # and generates TextClips. For now, we apply the background and audio safely.
    
    final_video = CompositeVideoClip([bg_clip]).set_audio(audio_clip)
    final_video.write_videofile(output_path, fps=30, codec="libx264", audio_codec="aac", preset="medium", threads=4)
    
    logger.info(f"Successfully rendered artifact to {output_path}")
    return output_path
