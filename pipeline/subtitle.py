import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageClip
from typing import Any

FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/calibri.ttf"
]

def load_font(size: int):
    for path in FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()

_dummy_img = Image.new("RGBA", (1, 1))
_dummy_draw = ImageDraw.Draw(_dummy_img)

def wrap_text(text: str, font: Any, max_width: int) -> str:
    words = text.split()
    lines, current = [], ""
    for w in words:
        test = current + " " + w if current else w
        bbox = _dummy_draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)
    return "\n".join(lines)

def render_text_image(text: str, fontsize=75, color=(255, 255, 255), stroke_color=(0, 0, 0), stroke_width=5, bg_color=(0, 0, 0), bg_opacity=0.65, max_width=900):
    font = load_font(fontsize)
    wrapped = wrap_text(text, font, max_width)
    tmp_img = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    tmp_draw = ImageDraw.Draw(tmp_img)
    bbox = tmp_draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=10, stroke_width=stroke_width)
    text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
    padding_x, padding_y = 28, 20
    img_width, img_height = text_width + 2 * padding_x, text_height + 2 * padding_y

    img = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    if bg_color is not None:
        draw.rounded_rectangle([0, 0, img_width - 1, img_height - 1], radius=22, fill=(*bg_color, int(bg_opacity * 255)))
    text_x = (img_width - text_width) // 2
    text_y = (img_height - text_height) // 2
    draw.multiline_text((text_x, text_y), wrapped, font=font, fill=color, stroke_width=stroke_width, stroke_fill=stroke_color, align="center", spacing=10)
    return np.array(img)

def create_text_clip(text: str, fontsize=75, color=(255, 255, 255), stroke_color=(0, 0, 0), stroke_width=5, bg_color=(0, 0, 0), bg_opacity=0.65, max_width=900):
    img = render_text_image(text, fontsize, color, stroke_color, stroke_width, bg_color, bg_opacity, max_width)
    return ImageClip(img, transparent=True)

def apply_pop_animation(clip: ImageClip, scale_factor=0.25, pop_duration=0.15) -> ImageClip:
    def scaler(t):
        if t <= pop_duration:
            return 1 + scale_factor * (1 - t / pop_duration)
        return 1.0
    return clip.resize(scaler)
