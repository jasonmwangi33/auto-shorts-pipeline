import os
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import AudioFileClip, ImageClip, CompositeVideoClip
from pipeline.visuals import VisualGenerator

class RenderResult:
    def __init__(self, video_path):
        self.video_path = video_path

class Renderer:
    def __init__(self):
        self.visual_gen = VisualGenerator()

    def _create_caption_clip(self, word_text, start_t, end_t, video_size=(1080, 1920)):
        w, h = video_size
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        font = None
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            "C:\\Windows\\Fonts\\impact.ttf",
            "C:\\Windows\\Fonts\\arialbd.ttf"
        ]
        
        for p in font_paths:
            if os.path.exists(p):
                try:
                    font = ImageFont.truetype(p, 85)  # Large, bold, single-word focus
                    break
                except: pass

        if font is None:
            font = ImageFont.load_default()

        text = word_text.upper()
        
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
        except:
            text_w, text_h = len(text) * 40, 90

        x = (w - text_w) / 2
        y = (h / 2) + 120  # Centered engagement zone

        # Vibrant yellow text with heavy black stroke outline for exact synchronization
        stroke_w = 9
        draw.text((x, y), text, font=font, fill="#FFE600", stroke_width=stroke_w, stroke_fill="black")

        img_np = np.array(img)
        duration = max(0.05, end_t - start_t)
        return ImageClip(img_np).set_start(start_t).set_duration(duration)

    def render_short(self, seed, output_path):
        audio_clip = AudioFileClip(seed["audio_path"])
        duration = audio_clip.duration

        bg_clip = self.visual_gen.generate_background(duration, seed)
        bar_clip = self.visual_gen.generate_progress_bar(duration)

        timings = seed.get("word_timings", [])
        caption_clips = []
        
        # Word-by-word precise synchronization to the dot
        if timings:
            for item in timings:
                w_text = item["word"]
                w_start = item["start"]
                w_end = item["end"]
                caption_clips.append(self._create_caption_clip(w_text, w_start, w_end))

        final_video = CompositeVideoClip([bg_clip, bar_clip] + caption_clips, size=(1080, 1920))
        final_video = final_video.set_audio(audio_clip).set_duration(duration)

        final_video.write_videofile(
            output_path,
            fps=30,
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",
            threads=4,
            logger=None
        )

        final_video.close()
        audio_clip.close()
        bg_clip.close()

        return RenderResult(output_path)
