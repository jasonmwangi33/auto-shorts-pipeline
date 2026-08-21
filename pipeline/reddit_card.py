import numpy as np
from PIL import Image, ImageDraw
from moviepy.editor import ImageClip
from .subtitle import load_font, wrap_text

def create_reddit_card(title: str, subreddit: str = "r/AmItheAsshole", author: str = "storyteller_99", upvotes: str = "24.1k", comments: str = "1.8k") -> np.array:
    card_w = 980
    pad_x = 45
    pad_y = 35
    
    font_sub = load_font(30)
    font_title = load_font(42)
    font_meta = load_font(28)

    max_text_w = card_w - (pad_x * 2)
    wrapped_title = wrap_text(title, font_title, max_text_w)
    
    dummy = Image.new("RGBA", (1, 1))
    draw_d = ImageDraw.Draw(dummy)
    bbox_title = draw_d.multiline_textbbox((0, 0), wrapped_title, font=font_title, spacing=10)
    title_h = bbox_title[3] - bbox_title[1]

    card_h = pad_y + 45 + 15 + title_h + 20 + 35 + pad_y
    card_img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card_img)

    # White Card Background
    draw.rounded_rectangle([0, 0, card_w - 1, card_h - 1], radius=28, fill=(255, 255, 255, 245), outline=(220, 220, 220, 255), width=2)

    # Reddit Logo (Orange Circle)
    draw.ellipse([pad_x, pad_y, pad_x + 40, pad_y + 40], fill=(255, 69, 0, 255))
    draw.text((pad_x + 12, pad_y + 4), "r/", font=font_sub, fill=(255, 255, 255, 255))

    # Header text
    header_str = f"{subreddit} • Posted by u/{author} • 5h ago"
    draw.text((pad_x + 55, pad_y + 4), header_str, font=font_sub, fill=(120, 124, 126, 255))

    # Story / Prompt Title
    text_y = pad_y + 45 + 15
    draw.multiline_text((pad_x, text_y), wrapped_title, font=font_title, fill=(28, 28, 28, 255), spacing=10)

    # Engagement pillboxes
    bottom_y = text_y + title_h + 20
    draw.rounded_rectangle([pad_x, bottom_y, pad_x + 160, bottom_y + 36], radius=18, fill=(240, 242, 245, 255))
    draw.text((pad_x + 18, bottom_y + 3), f"?  {upvotes}  ?", font=font_meta, fill=(80, 85, 90, 255))
    
    draw.rounded_rectangle([pad_x + 180, bottom_y, pad_x + 360, bottom_y + 36], radius=18, fill=(240, 242, 245, 255))
    draw.text((pad_x + 198, bottom_y + 3), f"??  {comments}", font=font_meta, fill=(80, 85, 90, 255))

    return np.array(card_img)

def generate_reddit_stamp_clip(title: str, subreddit: str, duration: float = 3.5) -> ImageClip:
    card_array = create_reddit_card(title, subreddit=subreddit)
    clip = ImageClip(card_array, transparent=True).set_duration(duration)
    return clip.set_position(("center", 0.14), relative=True)
