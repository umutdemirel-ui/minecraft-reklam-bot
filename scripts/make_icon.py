"""Regenerate the original geometric A/chat-bubble application icon; requires Pillow."""
from pathlib import Path

from PIL import Image, ImageDraw


def make_icon():
    image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((8, 8, 248, 248), radius=52, fill="#F04E45")
    draw.polygon([(62, 190), (109, 62), (148, 62), (195, 190), (157, 190),
                  (128, 103), (99, 190)], fill="#FFFFFF")
    draw.rounded_rectangle((106, 151, 153, 176), radius=5, fill="#FFFFFF")
    draw.polygon([(167, 207), (204, 207), (204, 231)], fill="#F04E45")
    target = Path(__file__).resolve().parent.parent / "assets" / "icon.ico"
    target.parent.mkdir(exist_ok=True)
    image.save(target, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    image.save(target.with_suffix(".png"))


if __name__ == "__main__":
    make_icon()
