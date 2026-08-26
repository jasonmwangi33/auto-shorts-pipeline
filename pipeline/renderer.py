import os
import random
import requests
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, concatenate_videoclips
from moviepy.video.fx.all import crop, resize

class RenderResult:
    def __init__(self, path):
        self.video_path = path

class Renderer:
    def __init__(self):
        self.workspace = "workspace"
        os.makedirs(self.workspace, exist_ok=True)
        self.pexels_key = os.getenv("PEXELS_API_KEY")

    def fetch_multiple_pexels(self, num_clips=4):
        print(f"[*] Fetching {num_clips} unique food videos from Pexels for a changing background...")
        headers = {"Authorization": self.pexels_key}
        url = "https://api.pexels.com/videos/search?query=satisfying+food+cooking+process&orientation=portrait&size=large&per_page=15"
        res = requests.get(url, headers=headers)
        if res.status_code != 200:
            raise RuntimeError(f"Pexels API failed: {res.status_code} {res.text}")
        
        videos = res.json().get("videos", [])
        random.shuffle(videos)
        
        downloaded = []
        for i, v in enumerate(videos[:num_clips]):
            link = v["video_files"][0]["link"]
            path = os.path.join(self.workspace, f"bg_{random.randint(1000,9999)}.mp4")
            with open(path, "wb") as f:
                f.write(requests.get(link).content)
            downloaded.append(path)
        return downloaded

    def render_short(self, seed, output_path):
        audio = AudioFileClip(seed["audio_path"])
        duration = audio.duration
        
        # 1. Background Generation (Stitching multiple clips)
        bg_paths = self.fetch_multiple_pexels(num_clips=5)
        clips = []
        for path in bg_paths:
            c = VideoFileClip(path, audio=False)
            # Standardize sizing for vertical short (1080x1920)
            if c.w / c.h > 1080/1920:
                c = crop(c, x_center=c.w/2, y_center=c.h/2, width=c.h*(1080/1920), height=c.h)
            c = resize(c, newsize=(1080, 1920))
            clips.append(c)
            
        final_bg = concatenate_videoclips(clips, method="compose")
        
        # If the stitched video is shorter than audio, loop it
        if final_bg.duration < duration:
            from moviepy.video.fx.all import loop
            final_bg = loop(final_bg, duration=duration)
        else:
            final_bg = final_bg.subclip(0, duration)
            
        final_bg = final_bg.set_audio(audio)

        # 2. Dead-Center Yellow Subtitle Generation
        print("[*] Burning centered yellow text word-by-word...")
        subtitle_clips = []
        for word_event in seed["word_timings"]:
            # Standardize text constraints
            txt = TextClip(
                word_event["word"].upper(),
                fontsize=110,
                color='yellow',
                font='Impact',
                stroke_color='black',
                stroke_width=5,
                method='caption',
                align='center',
                size=(900, None)
            )
            # Lock to exact center of the screen
            txt = txt.set_position('center').set_start(word_event["start"]).set_end(word_event["end"])
            subtitle_clips.append(txt)

        # 3. Composite and Render
        final_video = CompositeVideoClip([final_bg] + subtitle_clips)
        print(f"[*] Rendering final video to {output_path}...")
        final_video.write_videofile(
            output_path, 
            fps=30, 
            codec="libx264", 
            audio_codec="aac", 
            preset="ultrafast", 
            threads=4,
            logger=None
        )
        
        audio.close()
        final_bg.close()
        final_video.close()
        
        return RenderResult(output_path)
